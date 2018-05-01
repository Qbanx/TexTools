import bpy
import os
import bmesh
import math
import operator

from mathutils import Vector
from collections import defaultdict
from itertools import chain # 'flattens' collection of iterables

from . import utilities_uv




class op(bpy.types.Operator):
	bl_idname = "uv.textools_edge_split_bevel"
	bl_label = "Split Bevel"
	bl_description = "..."
	bl_options = {'REGISTER', 'UNDO'}

	radius = bpy.props.FloatProperty(
		name = "Space",
		description = "Space for split bevel",
		default = 0.015,
		min = 0,
		max = 1
	)


	@classmethod
	def poll(cls, context):
		if not bpy.context.active_object:
			return False

		#Only in Edit mode
		if bpy.context.active_object.mode != 'EDIT':
			return False

		#Requires UV map
		if not bpy.context.object.data.uv_layers:
			return False

		if bpy.context.scene.tool_settings.use_uv_select_sync:
			return False

		#Only in UV editor mode
		if bpy.context.area.type != 'IMAGE_EDITOR':
			return False

		return True


	def execute(self, context):
		main(self, self.radius)
		return {'FINISHED'}



def main(self, radius):

	#Store selection
	utilities_uv.selection_store()

	print("____________\nedge split UV sharp edges {}".format(radius))


	obj  = bpy.context.object
	bm = bmesh.from_edit_mesh(bpy.context.active_object.data);
	uvLayer = bm.loops.layers.uv.verify();
	
	islands = utilities_uv.getSelectionIslands()
	

	# Collect UV to Vert
	vert_to_uv = {}
	uv_to_vert = {}
	for face in bm.faces:
		for loop in face.loops:
			loop[uvLayer].select = True
			vert = loop.vert
			uv = loop[uvLayer]
			# vert_to_uv
			if vert not in vert_to_uv:
				vert_to_uv[vert] = [uv];
			else:
				vert_to_uv[vert].append(uv)
			# uv_to_vert
			if uv not in uv_to_vert:
				uv_to_vert[ uv ] = vert;


	# Collect hard edges
	edges = []
	for edge in bm.edges:
		if edge.select and not edge.smooth:
			# edge.link_faces
			# print("Hard edge: {} - {}".format(edge.verts[0].index, edge.verts[1].index))
			edges.append(edge)



	
	# edges = sort_edges(edges)

	for edge in edges:

		# Find faces that connect with both verts
		faces = []
		for face in edge.link_faces:
			if edge.verts[0] in face.verts and edge.verts[1] in face.verts:
				faces.append(face)

		if len(faces) == 2:
			print("Hard edge: {} -> {} = {}x faces".format(edge.verts[0].index, edge.verts[1].index, len(faces)))

			centers = [get_face_center(uvLayer, faces[0]), get_face_center(uvLayer, faces[1])]



	# print("islands {}x".format(len(islands)))
	# for island in islands:
	# 	print("I")
	# 	for face in island:
	# 		print("F")

	#Restore selection
	utilities_uv.selection_restore()


def get_face_center(uvLayer, face):
	center = Vector((0,0))
	for loop in face.loops:
		if loop[uvLayer].select is True:
			center+= loop[uvLayer].uv
	center/=len(face.loops)
	return center

# def sort_edges(edges):

# 	# Sort by connections
# 	vert_counts = {}
# 	vert_edges = {}
# 	print("--- Sort edges")

# 	for edge in edges:
# 		idx_A = edge.verts[0].index
# 		idx_B = edge.verts[1].index
		
# 		if idx_A not in vert_counts:
# 			vert_counts[idx_A] = 0
# 		if idx_B not in vert_counts:
# 			vert_counts[idx_B] = 0

# 		vert_counts[idx_A]+=1
# 		vert_counts[idx_B]+=1

# 		# if idx_A not in vert_edges:
# 		# 	vert_edges[edge]

# 	for key in vert_counts:
# 		print("#{}  =  {}x".format(key, vert_counts[key]))



