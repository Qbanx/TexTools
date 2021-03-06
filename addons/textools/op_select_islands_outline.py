import bpy
import bmesh
import operator
from mathutils import Vector
from collections import defaultdict
from math import pi

from . import utilities_uv


class op(bpy.types.Operator):
	bl_idname = "uv.textools_select_islands_outline"
	bl_label = "Select Overlap"
	bl_description = "Select overlapping islands"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		if not bpy.context.active_object:
			return False
		
		if bpy.context.active_object.type != 'MESH':
			return False

		#Requires UV map
		if not bpy.context.object.data.uv_layers:
			return False 

		#Only in UV editor mode
		if bpy.context.area.type != 'IMAGE_EDITOR':
			return False

		return True


	def execute(self, context):
		select_outline(context)
		return {'FINISHED'}


def select_outline(context):

	#Only in Edit mode
	if bpy.context.active_object.mode != 'EDIT':
		bpy.ops.object.mode_set(mode='EDIT')


	bpy.context.scene.tool_settings.use_uv_select_sync = False

	bm = bmesh.from_edit_mesh(bpy.context.active_object.data);
	uvLayer = bm.loops.layers.uv.verify();

	bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
	bpy.ops.mesh.select_all(action='DESELECT')

	# Store previous edge seams
	edges_seam = [edge for edge in bm.edges if edge.seam]
	

	# Create seams from islands
	bpy.ops.uv.seams_from_islands()
	edges_islands = [edge for edge in bm.edges if edge.seam]

	# Clear seams
	for edge in edges_islands:
		edge.seam = False

	# Select island edges
	bpy.ops.mesh.select_all(action='DESELECT')
	for edge in edges_islands:
		edge.select = True

	# Restore seam selection
	for edge in edges_seam:
		edge.seam = True