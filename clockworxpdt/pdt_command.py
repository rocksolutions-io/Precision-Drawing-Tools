# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

# ----------------------------------------------------------
# Author: Alan Odom (Clockmender)
# ----------------------------------------------------------

import bpy
from bpy.types import Operator, Panel, PropertyGroup
from mathutils import Vector
import bmesh
import numpy as np
from math import sin, cos, tan, acos, pi, sqrt
from mathutils.geometry import intersect_point_line
from .pdt_functions import (setMode, checkSelection, setAxis, updateSel, viewCoords, viewCoordsI,
                            viewDir, euler_to_quaternion, arcCentre, intersection, getPercent)

# Routine to Display Error Messages.
#
def oops(self, context):
    scene = context.scene
    self.layout.label(text=scene.pdt_error)

# Function to check for Valid Object and Selection History.
#
def obj_check(obj,scene,data):
    if obj == None:
        scene.pdt_error = "Select at least 1 Object"
        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
        return None,False
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        if data in ['s','S']:
            if len([e for e in bm.edges]) < 1:
                scene.pdt_error = "Select at Least 1 Edge"
                bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                return None,False
            else:
                return bm,True
        if len(bm.select_history) >= 1:
            if data not in ['e','E','g','G','d','D','s','S']:
                actV = checkSelection(1, bm, obj)
            else:
                verts = [v for v in bm.verts if v.select]
                if len(verts) > 0:
                    actV = verts[0]
                else:
                    actV = None
            if actV == None:
                scene.pdt_error = "Work in Vertex Mode"
                bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                return None,False
        elif data in ['c','C','n','N']:
            scene.pdt_error = "Select at least 1 Vertex Individually"
            bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
            return None,False
        return bm,True
    elif obj.mode == 'OBJECT':
        return None,True

# Function to set Working Axes when using Distance Command.
#
def disAng(vals,flip_a,plane,scene):
    dis_v = float(vals[0])
    ang_v = float(vals[1])
    if flip_a:
        if ang_v > 0:
            ang_v = ang_v - 180
        else:
            ang_v = ang_v + 180
        scene.pdt_angle = ang_v
    if plane == 'LO':
        vector_delta = viewDir(dis_v,ang_v)
    else:
        a1,a2,a3 = setMode(plane)
        vector_delta = Vector((0,0,0))
        vector_delta[a1] = vector_delta[a1] + (dis_v * cos(ang_v*pi/180))
        vector_delta[a2] = vector_delta[a2] + (dis_v * sin(ang_v*pi/180))
    return vector_delta

# Function to Run the Command Line Interpreter.
#
def command_run(self,context):
    # Execute for Command line
    scene = context.scene
    scene.pdt_error = "All is Good!"
    comm = scene.pdt_command
    # First Letter
    # C = Cursor G = Grab(move) N = New Vertex V = Extrude Vertices Only E = Extrude geometry
    # P = Move Pivot Point D = Duplicate geometry, S = Split Edges
    # Second Letter
    # A = Absolute D = Delta XYZ I = Distance at Angle
    if len(comm) < 3:
        scene.pdt_error = "Bad Command Format, not enough Characters"
        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
        return
    else:
        data = comm[0]
        if data not in ['c','C','d','D','e','E','g','G','n','N','p','P','v','V','s','S']:
            scene.pdt_error = "Bad Operator (1st Letter); C D E G N P S or V only"
            bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
            return
        mode = comm[1]
        if mode not in ['a','A','d','D','i','I','p','P']:
            scene.pdt_error = "Bad Mode (2nd Letter); A C or I only"
            bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
            return
        vals = comm[2:].split(',')
        ind = 0
        for r in vals:
            try:
                number = float(r)
                good = True
            except ValueError:
                vals[ind] = '0'
            ind = ind+1
        mode_s = scene.pdt_select
        flip_a = scene.pdt_flipangle
        flip_p = scene.pdt_flippercent
        ext_a = scene.pdt_extend
        plane = scene.pdt_plane
        # This bit needs looking at.
        if mode not in ['a','A'] or (data in ['s','S'] and mode in ['a','A']):
            obj = bpy.context.view_layer.objects.active
            bm,good = obj_check(obj,scene,data)
            if obj.mode == 'EDIT':
                if len(bm.select_history) < 1 and data in ['c','C','n','N','p','P']:
                    scene.pdt_error = "No Active Vertex - Not a Good Idea!"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
            if good:
                obj_loc = obj.matrix_world.decompose()[0]
            else:
                return

        if data in ['c','C','p','P']:
            # Cursor or Pivot Point
            if mode in ['a','A']:
                # Absolute Options
                if len(vals) != 3:
                    scene.pdt_error = "Bad Command - 3 Coords needed"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
                vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                if data in ['c','C']:
                    scene.cursor.location = vector_delta
                else:
                    scene.pdt_pivotloc = vector_delta
            elif mode in ['d','D']:
                # Delta Options
                if len(vals) != 3:
                    scene.pdt_error = "Bad Command - 3 Coords needed"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
                vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                if mode_s == 'REL':
                    if data in ['c','C']:
                        scene.cursor.location = scene.cursor.location + vector_delta
                    else:
                        scene.pdt_pivotloc = scene.pdt_pivotloc + vector_delta
                elif mode_s == 'SEL':
                    if obj.mode == 'EDIT':
                        if data in ['c','C']:
                            scene.cursor.location = bm.select_history[-1].co + obj_loc + vector_delta
                        else:
                            scene.pdt_pivotloc = bm.select_history[-1].co + obj_loc + vector_delta
                    elif obj.mode == 'OBJECT':
                        if data in ['c','C']:
                            scene.cursor.location = obj_loc + vector_delta
                        else:
                            scene.pdt_pivotloc = obj_loc + vector_delta
            elif mode in ['i','I']:
                # Direction Options
                if len(vals) != 2:
                    scene.pdt_error = "Bad Command - 2 Values needed"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
                vector_delta = disAng(vals,flip_a,plane,scene)
                if mode_s == 'REL':
                    if data in ['c','C']:
                        scene.cursor.location = scene.cursor.location + vector_delta
                    else:
                        scene.pdt_pivotloc =scene.pdt_pivotloc +vector_delta
                elif mode_s == 'SEL':
                    if obj.mode == 'EDIT':
                        if data in ['c','C']:
                            scene.cursor.location = bm.select_history[-1].co + obj_loc + vector_delta
                        else:
                            scene.pdt_pivotloc = bm.select_history[-1].co + obj_loc + vector_delta
                    elif obj.mode == 'OBJECT':
                        if data in ['c','C']:
                            scene.cursor.location = obj_loc + vector_delta
                        else:
                            scene.pdt_pivotloc = obj_loc + vector_delta
            elif mode in ['p','P']:
                # Percent Options
                if len(vals) != 1:
                    scene.pdt_error = "Bad Command - 1 Value needed"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
                vector_delta = getPercent(obj, flip_p, float(vals[0]), data, scene)
                if vector_delta == None:
                    return
                if obj.mode == 'EDIT':
                    if data in ['c','C']:
                        scene.cursor.location = obj_loc + vector_delta
                    else:
                        scene.pdt_pivotloc = obj_loc + vector_delta
                elif obj.mode == 'OBJECT':
                    if data in ['c','C']:
                        scene.cursor.location = vector_delta
                    else:
                        scene.pdt_pivotloc = vector_delta
            else:
                scene.pdt_error = "Not a Valid, or Sensible, Option!"
                bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                return

        elif data in ['g','G']:
            # Move Vertices or Objects
            if mode in ['a','A']:
                if len(vals) != 3:
                    scene.pdt_error = "Bad Command - 3 Coords needed"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
                vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                if obj.mode == 'EDIT':
                    verts = [v for v in bm.verts if v.select]
                    if len(verts) == 0:
                        scene.pdt_error = "Nothing Selected!"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    for v in verts:
                        v.co = vector_delta - obj_loc
                    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if v.select], dist=0.0001)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif obj.mode == 'OBJECT':
                    for ob in bpy.context.view_layer.objects.selected:
                        ob.location = vector_delta
            elif mode in ['d','D']:
                if len(vals) != 3:
                    scene.pdt_error = "Bad Command - 3 Coords needed"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
                vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                if obj.mode == 'EDIT':
                    bmesh.ops.translate(bm,
                    verts=[v for v in bm.verts if v.select],
                    vec=vector_delta)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif obj.mode == 'OBJECT':
                    for ob in bpy.context.view_layer.objects.selected:
                        ob.location = obj_loc + vector_delta
            elif mode in ['i','I']:
                if len(vals) != 2:
                    scene.pdt_error = "Bad Command - 2 Values needed"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
                vector_delta = disAng(vals,flip_a,plane,scene)
                if obj.mode == 'EDIT':
                    verts = [v for v in bm.verts if v.select]
                    if len(verts) == 0:
                        scene.pdt_error = "Nothing Selected!"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    bmesh.ops.translate(bm,
                        verts=verts,
                        vec=vector_delta)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif obj.mode == 'OBJECT':
                    for ob in bpy.context.view_layer.objects.selected:
                        ob.location = ob.location + vector_delta
            elif mode in ['p','P']:
                if obj.mode == 'OBJECT':
                    if len(vals) != 1:
                        scene.pdt_error = "Bad Command - 1 Value needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = getPercent(obj, flip_p, float(vals[0]), data, scene)
                    if vector_delta == None:
                        return
                    ob.location = vector_delta
            else:
                scene.pdt_error = "Not a Valid, or Sensible, Option!"
                bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                return

        elif data in ['n','N']:
            # Add New Vertex
            if obj.mode == 'EDIT':
                if mode in ['a','A']:
                    if len(vals) != 3:
                        scene.pdt_error = "Bad Command - 3 Coords needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                    vNew = vector_delta - obj_loc
                    nVert = bm.verts.new(vNew)
                    for v in [v for v in bm.verts if v.select]:
                        v.select_set(False)
                    nVert.select_set(True)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif mode in ['d','D']:
                    if len(vals) != 3:
                        scene.pdt_error = "Bad Command - 3 Coords needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                    vNew = bm.select_history[-1].co + vector_delta
                    nVert = bm.verts.new(vNew)
                    for v in [v for v in bm.verts if v.select]:
                        v.select_set(False)
                    nVert.select_set(True)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif mode in ['i','I']:
                    if len(vals) != 2:
                        scene.pdt_error = "Bad Command - 2 Values needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = disAng(vals,flip_a,plane,scene)
                    vNew = bm.select_history[-1].co + vector_delta
                    nVert = bm.verts.new(vNew)
                    for v in [v for v in bm.verts if v.select]:
                        v.select_set(False)
                    nVert.select_set(True)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif mode in ['p','P']:
                    if len(vals) != 1:
                        scene.pdt_error = "Bad Command - 1 Value needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = getPercent(obj, flip_p, float(vals[0]), data, scene)
                    vNew = vector_delta
                    nVert = bm.verts.new(vNew)
                    for v in [v for v in bm.verts if v.select]:
                        v.select_set(False)
                    nVert.select_set(True)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                else:
                    scene.pdt_error = "Not a Valid, or Sensible, Option!"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
            else:
                scene.pdt_error = "Only Add New Vertices in Edit Mode"
                bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                return

        elif data in ['s','S']:
            # Split Edges
            if obj.mode == 'EDIT':
                if mode in ['a','A']:
                    if len(vals) != 3:
                        scene.pdt_error = "Bad Command - 3 Coords needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                    edges = [e for e in bm.edges if e.select]
                    if len (edges) != 1:
                        scene.pdt_error = "Only Select 1 Edge"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    geom = bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1)
                    new_verts = [v for v in geom['geom_split'] if isinstance(v, bmesh.types.BMVert)]
                    nVert = new_verts[0]
                    nVert.co = vector_delta - obj_loc
                    for v in [v for v in bm.verts if v.select]:
                        v.select_set(False)
                    nVert.select_set(True)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif mode in ['d','D']:
                    if len(vals) != 3:
                        scene.pdt_error = "Bad Command - 3 Coords needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                    edges = [e for e in bm.edges if e.select]
                    faces = [f for f in bm.faces if f.select]
                    if len (faces) != 0:
                        scene.pdt_error = "You have a Face Selected, this would have ruined the Topology"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    if len (edges) < 1:
                        scene.pdt_error = "Select at Least 1 Edge"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    geom = bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1)
                    new_verts = [v for v in geom['geom_split'] if isinstance(v, bmesh.types.BMVert)]
                    for v in [v for v in bm.verts if v.select]:
                        v.select_set(False)
                    for v in new_verts:
                        v.select_set(False)
                    bmesh.ops.translate(bm,
                    verts=new_verts,
                    vec=vector_delta)
                    for v in [v for v in bm.verts if v.select]:
                        v.select_set(False)
                    for v in new_verts:
                        v.select_set(False)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif mode in ['i','I']:
                    if len(vals) != 2:
                        scene.pdt_error = "Bad Command - 2 Values needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = disAng(vals,flip_a,plane,scene)
                    edges = [e for e in bm.edges if e.select]
                    faces = [f for f in bm.faces if f.select]
                    if len (faces) != 0:
                        scene.pdt_error = "You have a Face Selected, this would have ruined the Topology"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    if len (edges) < 1:
                        scene.pdt_error = "Select at Least 1 Edge"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    geom = bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1)
                    new_verts = [v for v in geom['geom_split'] if isinstance(v, bmesh.types.BMVert)]
                    bmesh.ops.translate(bm,
                    verts=new_verts,
                    vec=vector_delta)
                    for v in [v for v in bm.verts if v.select]:
                        v.select_set(False)
                    for v in new_verts:
                        v.select_set(False)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif mode in ['p','P']:
                    if len(vals) != 1:
                        scene.pdt_error = "Bad Command - 1 Value needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = getPercent(obj, flip_p, float(vals[0]), data, scene)
                    if vector_delta == None:
                        return
                    edges = [e for e in bm.edges if e.select]
                    faces = [f for f in bm.faces if f.select]
                    if len (faces) != 0:
                        scene.pdt_error = "You have a Face Selected, this would have ruined the Topology"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    if len (edges) < 1:
                        scene.pdt_error = "Select at Least 1 Edge"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    geom = bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1)
                    new_verts = [v for v in geom['geom_split'] if isinstance(v, bmesh.types.BMVert)]
                    nVert = new_verts[0]
                    nVert.co = vector_delta
                    for v in [v for v in bm.verts if v.select]:
                        v.select_set(False)
                    nVert.select_set(True)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                else:
                    scene.pdt_error = "Not a Valid, or Sensible, Option!"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
            else:
                scene.pdt_error = "Only Split Edges in Edit Mode"
                bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                return

        elif data in ['v','V']:
            # Extrude Vertices
            if obj.mode == 'EDIT':
                if mode in ['a','A']:
                    if len(vals) != 3:
                        scene.pdt_error = "Bad Command - 3 Coords needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                    vNew = vector_delta - obj_loc
                    nVert = bm.verts.new(vNew)
                    for v in [v for v in bm.verts if v.select]:
                        nEdge = bm.edges.new([v,nVert])
                        v.select_set(False)
                    nVert.select_set(True)
                    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if v.select], dist=0.0001)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif mode in ['d','D']:
                    if len(vals) != 3:
                        scene.pdt_error = "Bad Command - 3 Coords needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                    verts = [v for v in bm.verts if v.select]
                    if len(verts) == 0:
                        scene.pdt_error = "Nothing Selected!"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    for v in verts:
                        nVert = bm.verts.new(v.co)
                        nVert.co = nVert.co + vector_delta
                        nEdge = bm.edges.new([v,nVert])
                        v.select_set(False)
                        nVert.select_set(True)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif mode in ['i','I']:
                    if len(vals) != 2:
                        scene.pdt_error = "Bad Command - 2 Values needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = disAng(vals,flip_a,plane,scene)
                    verts = [v for v in bm.verts if v.select]
                    if len(verts) == 0:
                        scene.pdt_error = "Nothing Selected!"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    for v in verts:
                        nVert = bm.verts.new(v.co)
                        nVert.co = nVert.co + vector_delta
                        nEdge = bm.edges.new([v,nVert])
                        v.select_set(False)
                        nVert.select_set(True)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif mode in ['p','P']:
                    vector_delta = getPercent(obj, flip_p, float(vals[0]), data, scene)
                    verts = [v for v in bm.verts if v.select]
                    if len(verts) == 0:
                        scene.pdt_error = "Nothing Selected!"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    nVert = bm.verts.new(vector_delta)
                    if ext_a:
                        for v in [v for v in bm.verts if v.select]:
                            nEdge = bm.edges.new([v,nVert])
                            v.select_set(False)
                    else:
                        nEdge = bm.edges.new([bm.select_history[-1],nVert])
                    nVert.select_set(True)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                else:
                    scene.pdt_error = "Not a Valid, or Sensible, Option!"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
            else:
                scene.pdt_error = "Only Add Extrude Vertices in Edit Mode"
                bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                return

        elif data in ['e','E']:
            # Extrude Geometry
            if obj.mode == 'EDIT':
                if mode in ['d','D']:
                    if len(vals) != 3:
                        scene.pdt_error = "Bad Command - 3 Coords needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                    verts = [v for v in bm.verts if v.select]
                    if len(verts) == 0:
                        scene.pdt_error = "Nothing Selected!"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    ret = bmesh.ops.extrude_face_region(bm, geom = (
                        [f for f in bm.faces if f.select]+
                        [e for e in bm.edges if e.select]+
                        [v for v in bm.verts if v.select]),
                        use_select_history = True)
                    geom_extr = ret["geom"]
                    verts_extr = [v for v in geom_extr if isinstance(v, bmesh.types.BMVert)]
                    edges_extr = [e for e in geom_extr if isinstance(e, bmesh.types.BMEdge)]
                    faces_extr = [f for f in geom_extr if isinstance(f, bmesh.types.BMFace)]
                    del ret
                    bmesh.ops.translate(bm,
                        verts=verts_extr,
                        vec=vector_delta)
                    updateSel(bm,verts_extr,edges_extr,faces_extr)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif mode in ['i','I']:
                    if len(vals) != 2:
                        scene.pdt_error = "Bad Command - 2 Values needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = disAng(vals,flip_a,plane,scene)
                    verts = [v for v in bm.verts if v.select]
                    if len(verts) == 0:
                        scene.pdt_error = "Nothing Selected!"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    ret = bmesh.ops.extrude_face_region(bm, geom = (
                        [f for f in bm.faces if f.select]+
                        [e for e in bm.edges if e.select]+
                        [v for v in bm.verts if v.select]),
                        use_select_history = True)
                    geom_extr = ret["geom"]
                    verts_extr = [v for v in geom_extr if isinstance(v, bmesh.types.BMVert)]
                    edges_extr = [e for e in geom_extr if isinstance(e, bmesh.types.BMEdge)]
                    faces_extr = [f for f in geom_extr if isinstance(f, bmesh.types.BMFace)]
                    del ret
                    bmesh.ops.translate(bm,
                        verts=verts_extr,
                        vec=vector_delta)
                    updateSel(bm,verts_extr,edges_extr,faces_extr)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                else:
                    scene.pdt_error = "Not a Valid, or Sensible, Option!"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return

        elif data in ['d','D']:
            # Duplicate Geometry
            if obj.mode == 'EDIT':
                if mode in ['d','D']:
                    if len(vals) != 3:
                        scene.pdt_error = "Bad Command - 3 Coords needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = Vector((float(vals[0]),float(vals[1]),float(vals[2])))
                    verts = [v for v in bm.verts if v.select]
                    if len(verts) == 0:
                        scene.pdt_error = "Nothing Selected!"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    ret = bmesh.ops.duplicate(bm, geom = (
                        [f for f in bm.faces if f.select]+
                        [e for e in bm.edges if e.select]+
                        [v for v in bm.verts if v.select]),
                        use_select_history = True)
                    geom_dupe = ret["geom"]
                    verts_dupe = [v for v in geom_dupe if isinstance(v, bmesh.types.BMVert)]
                    edges_dupe = [e for e in geom_dupe if isinstance(e, bmesh.types.BMEdge)]
                    faces_dupe = [f for f in geom_dupe if isinstance(f, bmesh.types.BMFace)]
                    del ret
                    bmesh.ops.translate(bm,
                        verts=verts_dupe,
                        vec=vector_delta)
                    updateSel(bm,verts_dupe,edges_dupe,faces_dupe)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                elif mode in ['i','I']:
                    if len(vals) != 2:
                        scene.pdt_error = "Bad Command - 2 Values needed"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    vector_delta = disAng(vals,flip_a,plane,scene)
                    verts = [v for v in bm.verts if v.select]
                    if len(verts) == 0:
                        scene.pdt_error = "Nothing Selected!"
                        bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                        return
                    ret = bmesh.ops.duplicate(bm, geom = (
                        [f for f in bm.faces if f.select]+
                        [e for e in bm.edges if e.select]+
                        [v for v in bm.verts if v.select]),
                        use_select_history = True)
                    geom_dupe = ret["geom"]
                    verts_dupe = [v for v in geom_dupe if isinstance(v, bmesh.types.BMVert)]
                    edges_dupe = [e for e in geom_dupe if isinstance(e, bmesh.types.BMEdge)]
                    faces_dupe = [f for f in geom_dupe if isinstance(f, bmesh.types.BMFace)]
                    del ret
                    bmesh.ops.translate(bm,
                        verts=verts_dupe,
                        vec=vector_delta)
                    updateSel(bm,verts_dupe,edges_dupe,faces_dupe)
                    bmesh.update_edit_mesh(obj.data)
                    bm.select_history.clear()
                else:
                    scene.pdt_error = "Not a Valid, or Sensible, Option!"
                    bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                    return
            else:
                scene.pdt_error = "Only Duplicate Geometry in Edit Mode"
                bpy.context.window_manager.popup_menu(oops, title="Error", icon='ERROR')
                return
