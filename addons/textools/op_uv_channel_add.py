import bpy
import bmesh
import operator
from mathutils import Vector
from collections import defaultdict
from math import pi

from . import utilities_ui

class op(bpy.types.Operator):
	bl_idname = "uv.textools_uv_channel_add"
	bl_label = "Add UV Channel"
	bl_description = "Add a new UV channel with smart UV projected UV's and padding."
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		if bpy.context.active_object == None:
			return False
		if bpy.context.active_object.type != 'MESH':
			return False
		return True


	@classmethod
	def poll(cls, context):
		if bpy.context.active_object == None:
			return False
		if bpy.context.active_object.type != 'MESH':
			return False
		if  len(bpy.context.selected_objects) != 1:
			return False

		return True

	def execute(self, context):
		print("Add UV")
		
		if bpy.context.active_object.mode != 'EDIT':
			bpy.ops.object.mode_set(mode='EDIT')

		# Smart project UV's
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.uv.smart_project(
			angle_limit=65, 
			island_margin=0.5, 
			user_area_weight=0, 
			use_aspect=True, 
			stretch_to_bounds=True
		)

		# Re-Apply padding as normalized values
		bpy.ops.uv.select_all(action='SELECT')
		bpy.ops.uv.pack_islands(margin=utilities_ui.get_padding())


		return {'FINISHED'}

