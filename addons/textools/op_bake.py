import bpy
import os
import bmesh
from mathutils import Vector
from collections import defaultdict
from math import pi
from random import random
from mathutils import Color

from . import settings
from . import utilities_bake


# Notes: https://docs.blender.org/manual/en/dev/render/blender_render/bake.html
modes={
	'normal_tangent':	utilities_bake.BakeMode('',					type='NORMAL', color=(0.5, 0.5, 1, 1)),
	'normal_object': 	utilities_bake.BakeMode('',					type='NORMAL', color=(0.5, 0.5, 1, 1), normal_space='OBJECT' ),
	'cavity': 			utilities_bake.BakeMode('bake_cavity',		type='EMIT', setVertexColor=utilities_bake.setup_vertex_color_dirty),
	'dust': 			utilities_bake.BakeMode('bake_dust',		type='EMIT', setVertexColor=utilities_bake.setup_vertex_color_dirty),
	'worn':				utilities_bake.BakeMode('bake_worn',		type='EMIT', setVertexColor=utilities_bake.setup_vertex_color_dirty),
	'gradient_z':		utilities_bake.BakeMode('bake_gradient_z',	type='EMIT', ),
	'id_element':		utilities_bake.BakeMode('bake_id_element',	type='EMIT', setVertexColor=utilities_bake.setup_vertex_color_ids),
	'diffuse':			utilities_bake.BakeMode('',					type='DIFFUSE'),
	'ao':				utilities_bake.BakeMode('',					type='AO')
}


class op(bpy.types.Operator):
	bl_idname = "uv.textools_bake"
	bl_label = "Bake"
	bl_description = "Bake selected objects"

	@classmethod
	def poll(cls, context):
		if len(settings.sets) == 0:
			return False
		return True

	def execute(self, context):


		if settings.bake_mode not in modes:
			self.report({'ERROR_INVALID_INPUT'}, "Uknown mode '{}' only available: '{}'".format(settings.bake_mode, ", ".join(modes.keys() )) )
			return

		# Store Selection
		selected_objects 	= [obj for obj in bpy.context.selected_objects]
		active_object 		= bpy.context.scene.objects.active
		utilities_bake.store_bake_settings()

		# Render sets
		render(
			self = self, 
			mode = settings.bake_mode,

			size = bpy.context.scene.texToolsSettings.size, 

			bake_single = bpy.context.scene.texToolsSettings.bake_force_single,
			sampling_scale = int(bpy.context.scene.texToolsSettings.bake_sampling),
			samples = bpy.context.scene.texToolsSettings.bake_samples,
			ray_distance = bpy.context.scene.texToolsSettings.bake_ray_distance
		)
		
		# Restore selection
		utilities_bake.restore_bake_settings()
		bpy.ops.object.select_all(action='DESELECT')
		for obj in selected_objects:
			obj.select = True
		if active_object:
			bpy.context.scene.objects.active = active_object

		return {'FINISHED'}



def render(self, mode, size, bake_single, sampling_scale, samples, ray_distance):

	print("Bake '{}'".format(mode))

	# Setup
	if bpy.context.scene.render.engine != 'CYCLES':
		bpy.context.scene.render.engine = 'CYCLES'
	bpy.context.scene.cycles.samples = samples

	# Disable edit mode
	if bpy.context.scene.objects.active != None and bpy.context.object.mode != 'OBJECT':
	 	bpy.ops.object.mode_set(mode='OBJECT')

	# Get the baking sets / pairs
	sets = settings.sets

	# print("________________________________\nBake {}x '{}' at {} x {}".format(len(sets), mode, width, height))

	render_width = sampling_scale * size[0]
	render_height = sampling_scale * size[1]

	for s in range(0,len(sets)):
		set = sets[s]

		# Get image name
		name_texture = "{}_{}".format(set.name, mode)
		if bake_single:
			name_texture = "{}_{}".format(sets[0].name, mode)# In Single mode bake into same texture
		path = bpy.path.abspath("//{}.tga".format(name_texture))

		# Requires 1+ low poly objects
		if len(set.objects_low) == 0:
			self.report({'ERROR_INVALID_INPUT'}, "No low poly object as part of the '{}' set".format(set.name) )
			return

		# Check for UV maps
		for obj in set.objects_low:
			if len(obj.data.uv_layers) == 0:
				self.report({'ERROR_INVALID_INPUT'}, "No UV map available for '{}'".format(obj.name))
				return

		# Check for cage inconsistencies
		if len(set.objects_cage) > 0 and (len(set.objects_low) != len(set.objects_cage)):
			self.report({'ERROR_INVALID_INPUT'}, "{}x cage objects do not match {}x low poly objects for '{}'".format(len(set.objects_cage), len(set.objects_low), obj.name))
			return

		# Get Materials
		material_loaded = get_material(mode)
		material_empty = None
		if "TT_bake_node" in bpy.data.materials:
			material_empty = bpy.data.materials["TT_bake_node"]
		else:
			material_empty = bpy.data.materials.new(name="TT_bake_node")

		# Assign Materials to Objects
		if (len(set.objects_high) + len(set.objects_float)) == 0:
			# Low poly bake: Assign material to lowpoly
			for obj in set.objects_low:
				assign_vertex_color(mode, obj)
				assign_material(obj, [material_loaded, material_empty])
		else:
			# High to low poly: Low poly require empty material to bake into image
			for obj in set.objects_low:
				assign_material(obj, [material_empty])

			# Assign material to highpoly
			for obj in (set.objects_high+set.objects_float):
				assign_vertex_color(mode, obj)
				assign_material(obj, [material_loaded])


		# Setup Image
		is_clear = (not bake_single) or (bake_single and s==0)
		image = setup_image(mode, name_texture, render_width, render_height, path, is_clear)

		# Assign bake node to Material
		setup_image_bake_node(set.objects_low[0], image)
		

		print("Bake '{}' = {}".format(set.name, path))

		# Bake each low poly object in this set
		for i in range(len(set.objects_low)):
			obj_low = set.objects_low[i]
			obj_cage = None if i >= len(set.objects_cage) else set.objects_cage[i]

			bpy.context.scene.objects.active = obj_low

			bpy.ops.object.select_all(action='DESELECT')
			for obj_high in (set.objects_high):
				obj_high.select = True
			obj_low.select = True
			cycles_bake(
				mode, 
				bpy.context.scene.texToolsSettings.padding,
				sampling_scale, 
				samples, 
				ray_distance,
				 len(set.objects_high) > 0, 
				 obj_cage
			)

			# Bake Floaters seperate?
			if len(set.objects_float) > 0:
				bpy.ops.object.select_all(action='DESELECT')
				for obj_high in (set.objects_float):
					obj_high.select = True
				obj_low.select = True
				cycles_bake(
					mode, 
					0,
					sampling_scale, 
					samples, 
					ray_distance, 
					len(set.objects_float) > 0,
					 obj_cage
				)


		# Downsample image?
		if not bake_single or (bake_single and s == len(sets)-1):
			# When baking single, only downsample on last bake
			if render_width != size[0] or render_height != size[1]:
				image.scale(width,height)
			
			# image.save()
		


def setup_image(mode, name, width, height, path, is_clear):#
	image = None

	print("Path "+path)
	# if name in bpy.data.images and bpy.data.images[name].has_data == False:
	# 	# Previous image does not have data, remove first
	# 	print("Image pointer exists but no data "+name)
	# 	image = bpy.data.images[name]
	# 	image.update()
		# image.generated_height = height

		# bpy.data.images.remove(bpy.data.images[name])

	if name not in bpy.data.images:
		# Create new image
		image = bpy.data.images.new(name, width=width, height=height)

	else:
		# Reuse existing Image
		image = bpy.data.images[name]
		# Reisze?
		if image.size[0] != width or image.size[1] != height or image.generated_width != width or image.generated_height != height:
			image.generated_width = width
			image.generated_height = height
			image.scale(width, height)

	# Fill with plain color
	if is_clear:
		image.generated_color = modes[mode].color
		image.generated_type = 'BLANK'


	image.file_format = 'TARGA'

	# TODO: Verify that the path exists
	# image.filepath_raw = path

	return image



def setup_image_bake_node(obj, image):
	if len(obj.data.materials) <= 0:
			print("ERROR, need spare material to setup active image texture to bake!!!")
	else:
		for slot in obj.material_slots:
			if slot.material:
				slot.material.use_nodes = True

				# Assign bake node
				tree = slot.material.node_tree
				node = None
				if "bake" in tree.nodes:
					node = tree.nodes["bake"]
				else:
					node = tree.nodes.new("ShaderNodeTexImage")
				node.name = "bake"
				node.select = True
				node.image = image
				tree.nodes.active = node



def assign_vertex_color(mode, obj):
	if modes[mode].setVertexColor:
		modes[mode].setVertexColor(obj)



def assign_material(obj, preferred_materials):
	if len(obj.data.materials) == 0:
		for material in preferred_materials:
			if material:
				# Take the first available material
				obj.data.materials.append(material)
				obj.active_material_index = len(obj.data.materials)-1
				return



def get_material(mode):
	if modes[mode].material == "":
		return None # No material setup requires

	# Find or load material
	name = modes[mode].material
	path = os.path.join(os.path.dirname(__file__), "resources/materials.blend")+"\\Material\\"
	if bpy.data.materials.get(name) is None:
		print("Material not yet loaded: "+mode)
		bpy.ops.wm.append(filename=name, directory=path, link=False, autoselect=False)

	return bpy.data.materials.get(name)




def cycles_bake(mode, padding, sampling_scale, samples, ray_distance, is_multi, obj_cage):
	# Set samples
	bpy.context.scene.cycles.samples = samples

	# Speed up samples for simple render modes
	if modes[mode].type == 'EMIT' or modes[mode].type == 'DIFFUSE':
		bpy.context.scene.cycles.samples = 1

	# Pixel Padding
	bpy.context.scene.render.bake.margin = padding * sampling_scale

	# Disable Direct and Indirect for all 'DIFFUSE' bake types
	if modes[mode].type == 'DIFFUSE':
		bpy.context.scene.render.bake.use_pass_direct = False
		bpy.context.scene.render.bake.use_pass_indirect = False
		bpy.context.scene.render.bake.use_pass_color = True

	if obj_cage is None:
		# Bake with Cage
		bpy.ops.object.bake(
			type=modes[mode].type, 
			use_clear=False, 
			cage_extrusion=ray_distance, 

			use_selected_to_active=is_multi, 
			normal_space=modes[mode].normal_space
		)
	else:
		# Bake without Cage
		bpy.ops.object.bake(
			type=modes[mode].type, 
			use_clear=False, 
			cage_extrusion=ray_distance, 

			use_selected_to_active=is_multi, 
			normal_space=modes[mode].normal_space,

			#Use Cage and assign object
			use_cage=True, 	
			cage_object=obj_cage.name
		)


