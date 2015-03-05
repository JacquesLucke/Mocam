'''
Copyright (C) 2014 Jacques Lucke
mail@jlucke.com

Created by Jacques Lucke

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    

Naming convention:
    camera - the camera object, that means with properties like location, etc.
    camera_data - camera.data
    mocam - camera.data.mocam
'''


import bpy
import random
import math
from bpy.app.handlers import persistent
from bpy.props import *
from operator import attrgetter
from mathutils import Matrix, Vector

@persistent
def correct_target_lists(scene):
    for mocam in get_active_mocams():
        mocam.correct_target_list()
        mocam.update(scene.frame_current_final)

def get_selected_mocam():
    camera = get_selected_camera()
    if camera:
        return Mocam(camera)
    
def get_selected_camera():
    cameras = get_cameras()
    if len(cameras) == 0:
        return None
    elif len(cameras) == 1:
        return cameras[0]
    scene = bpy.context.scene
    return scene.objects.get(scene.mocam.selected_camera_name)

def get_active_mocams():
    return [Mocam(camera) for camera in get_cameras() if camera.data.mocam.active]
def get_camera_names():
    return [camera.name for camera in get_cameras()]
def get_cameras():
    return [object for object in bpy.context.scene.objects if object.type == "CAMERA"]


class Mocam:
    def __init__(self, camera):
        self.camera = camera
        self.props = camera.data.mocam
        
    def update(self, frame):
        calculator = MocamCalculator(self)
        result = calculator.calculate(frame)
        self.set_calculation_result(result)
        
    def set_calculation_result(self, result):
        self.camera.matrix_world = result.matrix_world
        self.camera.data.dof_distance = result.focus_distance
        
    def add_target(self, object):
        ObjectFinder.create_first_identifier(object)
       
        item = self.props.targets.add()
        item.index = len(self.props.targets)
        item.object.object_name = object.name
        item.object.identifier = object.mocam.identifier
        ObjectFinder.correct_item_and_object(item.object)
        
    def get_targets(self):
        return TargetList(self.props.targets)
    
    def correct_target_list(self):
        target_list = TargetList(self.props.targets)
        self.correct_target_objects()
        self.remove_targets_without_object()
        self.set_correct_indices()
        
    def correct_target_objects(self):
        for target in self.props.targets:
            ObjectFinder.correct_item_and_object(target.object)
        
    def remove_targets_without_object(self):
        remove_indices = []
        for i, item in enumerate(self.props.targets):
            target = Target(item)
            if not target.object:
                remove_indices.append(i - len(remove_indices))
        for index in remove_indices:
            self.props.targets.remove(index)
            
    def set_correct_indices(self):
        items = list(self.props.targets)
        items.sort(key = attrgetter("index"))
        for i, item in enumerate(items):
            item.index = i
            
    def get_target_from_index(self, index):
        item = self.get_target_item_from_index(index)
        if item:
            return Target(item)
            
    def get_target_item_from_index(self, index):
        for item in self.props.targets:
            if item.index == index:
                return item
            
    def remove_target_with_index(self, index):
        prop_index = -1
        for item in self.props.targets:
            if item.index == index:
                prop_index = item.index
                break
        self.props.targets.remove(prop_index)
        self.set_correct_indices()
        
    def change_indices(self, index_a, index_b):
        item_a = self.get_target_item_from_index(index_a)
        item_b = self.get_target_item_from_index(index_b)
        if item_a and item_b:
            item_a.index = index_b
            item_b.index = index_a
            
    def get_move_item(self, index):
        self.create_missing_move_items(index + 1)
        return self.props.moves[index]
                
    def create_missing_move_items(self, amount):
        move_items = self.props.moves
        missing_items_amount = max(amount - len(move_items), 0)
        for i in range(missing_items_amount):
            item = move_items.add()
            if len(move_items) == 1:
                item.load = 0    
            
    def get_move_data(self, frame):
        self.create_missing_move_items(len(self.props.targets))
        move_data = MoveData()
        
        frame_counter = 0
        move, index = None, -1
        for index, move in enumerate(self.props.moves):
            frame_counter += move.load + move.stay
            if frame_counter > frame:
                break
         
        if move is not None:   
            move_data.move = move
            move_data.frame_in_move = frame - (frame_counter - move.load - move.stay)
            move_data.target_start = self.get_target_from_index(index - 1)
            move_data.target_end = self.get_target_from_index(index)      
        return move_data
        
    @property
    def active(self):
        return self.props.active
    @active.setter
    def active(self, active):
        self.props.active = active
        
    @property
    def properties(self):
        return self.props
    
    
class MoveData:
    def __init__(self):
        self.target_start = None
        self.target_end = None
        self.move = None
        self.frame_in_move = 0
        
    @property
    def has_no_targets(self):
        return self.target_start is None and self.target_end is None
    
    @property
    def is_first_target(self):
        return self.target_start is None and self.target_end is not None
    
    @property
    def is_last_target(self):
        return self.target_start is not None and self.target_end is None
    
    @property
    def has_both_targets(self):
        return self.target_start is not None and self.target_end is not None
    
    @property
    def is_moving(self):
        if self.move:
            return self.frame_in_move < self.move.load
        return False
    
    @property
    def move_progress(self):
        progress = self.frame_in_move / self.move.load 
        return min(max(progress, 0), 1)
    
    
class MocamCalculator:
    def __init__(self, mocam):
        self.mocam = mocam
        
    def calculate(self, frame):
        result = CalculationResult()
        move_data = self.mocam.get_move_data(frame)
        
        if move_data.has_no_targets:
            return result
        
        transition = Matrix.Identity(4)
        view = Matrix.Identity(4)
        
        if move_data.has_no_targets:
            pass
        elif move_data.is_first_target:
            transition = move_data.target_end.position_matrix
            view = move_data.target_end.view_matrix
        elif move_data.is_last_target:
            transition = move_data.target_start.position_matrix
            view = move_data.target_start.view_matrix           
        elif move_data.has_both_targets:
            start = move_data.target_start
            end = move_data.target_end
            
            if move_data.is_moving:
                move_progress = move_data.move_progress
                transition = start.position_matrix.lerp(end.position_matrix, move_progress)
                view = start.view_matrix.lerp(end.view_matrix, move_progress)
            else:
                transition = move_data.target_end.position_matrix
                view = move_data.target_end.view_matrix
       
        
        result.matrix_world = transition * view
        result.focus_distance = 5
        return result
    
    def calc_transition_matrix(self, start_target, end_target, factor):
        start_matrix = start_target.position_matrix
        end_matrix = end_target.position_matrix
        return start_matrix.lerp(end_matrix, factor)
    
    def calc_target_view_matrix(self, start_target, end_target, factor):
        return Matrix.Translation(Vector((0, 0, 5)))
        
    
class CalculationResult:
    def __init__(self):
        self.matrix_world = Matrix.Identity(4)
        self.focus_distance = 1 
    
    
class ObjectFinder:    
    @classmethod
    def get_object(cls, item):
        object = cls.get_object_by_name(item.object_name)
        if object:
            return object
        objects = cls.get_objects_with_identifier(item.identifier)
        if len(objects) > 0:
            return objects[0]
    
    @classmethod    
    def correct_item_and_object(cls, item):
        objects = cls.get_objects_with_identifier(item.identifier)
        amount = len(objects)
        if amount == 0:
            item.object_name = ""
            item.identifier = -1
        elif amount == 1:
            item.object_name = objects[0].name
            item.identifier = objects[0].mocam.identifier
        else:
            objects_with_wrong_name = [object for object in objects if object.name != item.object_name]
            if len(objects) == len(objects_with_wrong_name):
                item.object_name = objects[0].name
                objects_with_wrong_name = objects_with_wrong_name[1:]
            for object in objects_with_wrong_name:
                cls.set_new_identifier(object)
    
    @classmethod
    def create_first_identifier(cls, object):
        if object.mocam.identifier == 0:
            cls.set_new_identifier(object) 
    @classmethod
    def set_new_identifier(cls, object):
        object.mocam.identifier = round(random.random() * 1000000)
        
    @classmethod
    def get_object_by_name(cls, name):
        return bpy.data.objects.get(name)
    @classmethod
    def get_objects_with_identifier(cls, identifier):
        return [object for object in bpy.data.objects if object.mocam.identifier == identifier]
    
class TargetList:
    def __init__(self, target_items):
        self.target_items = target_items
        self.targets = [target for target in self.get_all_targets() if target.object]
        
    def get_all_targets(self):
        targets = []
        for item in self.target_items:
            targets.append(Target(item))
        targets.sort(key = attrgetter("index"))
        return targets   
    
    def contains_object(self, object):
        for target in self.targets:
            if target.object == object:
                return True
        return False
    
    def find_targets_with_objects(self, objects):
        found_targets = []
        for object in objects:
            found_targets.extend(self.find_targets_with_object(object))
        return found_targets
    
    def find_targets_with_object(self, object):
        return [target for target in self.targets if target.object == object]
    
    def __getitem__(self, key):
        return self.targets[key]
    
    def __len__(self):
        return len(self.targets)
    
    
class Target:
    def __init__(self, target_item):
        self.object = ObjectFinder.get_object(target_item.object)
        self.index = target_item.index
        self.position = Matrix.Identity(4)
        
    @property
    def position_matrix(self):
        if self.position == Matrix.Identity(4):
            self.position = self.get_object_matrix()
        return self.position
    
    @property
    def view_matrix(self):
        return Matrix.Translation(Vector((0, 0, 5)))
    
    def get_object_matrix(self):
        bound_center = self.calc_bounding_box_center()
        return self.object.matrix_world * Matrix.Translation(bound_center)       
    
    def calc_bounding_box_center(self):
        center = sum((Vector(b) for b in self.object.bound_box), Vector())
        return center / 8   



class MocamPanel(bpy.types.Panel):
    bl_idname = "MocamPanel"
    bl_label = "Mocam"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Tools"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        cameras = get_cameras()
        camera_amount = len(cameras)
        
        if camera_amount == 0:
            layout.operator("mocam.new_active_camera", "New Mocam")
        elif camera_amount >= 2:
            layout.prop(scene.mocam, "selected_camera_name", text = "Display")
        
        mocam = get_selected_mocam()    
        if not mocam:
            return
        
        layout.prop(mocam.properties, "active", text = "Is Camera Active")
        
        if not mocam.active:
            return
        
        targets = mocam.get_targets()
        col = layout.column(align = True)
        for target in targets:
            row = col.row(align = True)
            if scene.mocam.enable_renaming:
                operator = row.operator("mocam.select_and_goto_index", text = "", icon = "EYEDROPPER")
                operator.index = target.index
                row.prop(target.object, "name", text = "")
                if target.object.type == "FONT":
                    operator = row.operator("mocam.object_name_to_text", text = "", icon = "OUTLINER_DATA_FONT")
                    operator.index = target.index
                    operator = row.operator("mocam.object_text_to_name", text = "", icon = "OUTLINER_OB_FONT")
                    operator.index = target.index
            else:
                operator = row.operator("mocam.move_target", text = "", icon = "TRIA_UP")
                operator.index_from = target.index
                operator.index_to = max(target.index - 1, 0)
                
                operator = row.operator("mocam.move_target", text = "", icon = "TRIA_DOWN")
                operator.index_from = target.index
                operator.index_to = min(target.index + 1, len(targets) - 1)
                    
                operator = row.operator("mocam.select_and_goto_index", text = target.object.name)
                operator.index = target.index
                    
                operator = row.operator("mocam.remove_target", text = "", icon = "X")
                operator.index = target.index
        
        row = col.row(align = True)
        row.operator("mocam.add_targets", text = "From Selection", icon = "PLUS")
        
        try:
            if len(context.active_object.data.body.split("\n")) >= 2:
                row = col.row(align = True)
                row.operator("mocam.separate_text_and_add_targets", text = "From Text Lines", icon = "PLUS")
        except: pass
            
        layout.prop(scene.mocam, "enable_renaming")
        
        selected_targets = targets.find_targets_with_objects(context.selected_objects)
        selected_targets.sort(key = attrgetter("index"))
        
        for target in selected_targets:
            move_item = mocam.get_move_item(target.index)
            box = layout.box()
            col = box.column(align = True)
            col.label("\"" + target.object.name + "\"")
            if target.index > 0:
                col.prop(move_item, "load")
            if target.index < len(targets) - 1:
                col.prop(move_item, "stay")
            
     
# operators     
        
class NewActiveCamera(bpy.types.Operator):
    bl_idname = "mocam.new_active_camera"
    bl_label = "New Mocam"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def execute(self, context):
        bpy.ops.object.camera_add()
        mocam = Mocam(context.active_object)
        mocam.active = True
        return {"FINISHED"}
                
                
class AddSelectedObjectsAsTargets(bpy.types.Operator):
    bl_idname = "mocam.add_targets"
    bl_label = "Add Targets"
    bl_description = "Use selected objects as targets"
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def execute(self, context):
        mocam = get_selected_mocam()
        if mocam:
            for object in reversed(context.selected_objects):
                if object != mocam.camera:
                    mocam.add_target(object)
        return {"FINISHED"}
    
    
class SelectAndGotoIndex(bpy.types.Operator):
    bl_idname = "mocam.select_and_goto_index"
    bl_label = "Select and Goto Index"
    bl_description = "Jump to this target (ctrl/shift to select all/more)"
    bl_options = {"REGISTER"}
    
    index = IntProperty(name = "Index", default = 0)
    
    @classmethod
    def poll(cls, context):
        return True
    
    def invoke(self, context, event):
        mocam = get_selected_mocam()
        if mocam:
            if not event.shift:
                bpy.ops.object.select_all(action = "DESELECT")
            
            target = mocam.get_target_from_index(self.index)
            if target:
                self.select_target(target)
                self.jump_to_target(target)
                
            if event.ctrl:
                for target in mocam.get_targets():
                    self.select_target(target)
                   
        return {"FINISHED"}
    
    def select_target(self, target):
        target.object.select = True
        bpy.context.scene.objects.active = target.object
        
    def jump_to_target(self, target):
        pass
            
            
class RemoveTarget(bpy.types.Operator):
    bl_idname = "mocam.remove_target"
    bl_label = "Remove Target"
    bl_description = "Remove this target"
    bl_options = {"REGISTER"}
    
    index = IntProperty(name = "Index", default = 0)
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        mocam = get_selected_mocam()
        if mocam:
            mocam.remove_target_with_index(self.index)
        return {"FINISHED"} 
    
    
class ObjectNameToText(bpy.types.Operator):
    bl_idname = "mocam.object_name_to_text"
    bl_label = "Object Name to Text"
    bl_description = "Use the name as text (hold ctrl/alt/shift for all text objects)"
    bl_options = {"REGISTER"}
    
    index = IntProperty(name = "Index", default = 0)
    
    @classmethod
    def poll(cls, context):
        return True
    
    def invoke(self, context, event):
        mocam = get_selected_mocam()
        if mocam:
            objects = []
            
            if event.ctrl or event.alt or event.shift:
                objects = [target.object for target in mocam.get_targets()]
            else:
                target = mocam.get_target_from_index(self.index)
                if target:
                    objects = [target.object]
            
            for object in objects:
                if object.type == "FONT":
                    object.data.body = object.name
        return {"FINISHED"}      
    
    
class ObjectNameToText(bpy.types.Operator):
    bl_idname = "mocam.object_text_to_name"
    bl_label = "Text to Object Name"
    bl_description = "Use the text as name (hold ctrl/alt/shift for all text objects)"
    bl_options = {"REGISTER"}
    
    index = IntProperty(name = "Index", default = 0)
    
    @classmethod
    def poll(cls, context):
        return True
    
    def invoke(self, context, event):
        mocam = get_selected_mocam()
        if mocam:
            objects = []
            
            if event.ctrl or event.alt or event.shift:
                objects = [target.object for target in mocam.get_targets()]
            else:
                target = mocam.get_target_from_index(self.index)
                if target:
                    objects = [target.object]
            
            for object in objects:
                if object.type == "FONT":
                    object.name = object.data.body
        return {"FINISHED"}     
    
    
class MoveTarget(bpy.types.Operator):
    bl_idname = "mocam.move_target"
    bl_label = "Move Target"
    bl_description = "Move this Target"
    bl_options = {"REGISTER"}
    
    index_from = IntProperty(name = "Index From", default = 0)
    index_to = IntProperty(name = "Index To", default = 0)
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def execute(self, context):
        mocam = get_selected_mocam()
        if mocam:
            mocam.change_indices(self.index_from, self.index_to)
        return {"FINISHED"}
                     
                     
class SeparateTextAndAddTargets(bpy.types.Operator):
    bl_idname = "mocam.separate_text_and_add_targets"
    bl_label = "Separate Text and Add Targets"
    bl_description = ""
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and getattr(context.active_object, "type", "") == "FONT"
    
    def execute(self, context):
        bpy.ops.mocam.separate_text_lines()
        bpy.ops.mocam.add_targets()
        return {"FINISHED"}
                             
                     
                        
class SeparateTextLines(bpy.types.Operator):
    bl_idname = "mocam.separate_text_lines"
    bl_label = "Separate Text Lines"
    bl_description = "Create a text object for each line in the active object"
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and getattr(context.active_object, "type", "") == "FONT"
    
    def execute(self, context):
        bpy.ops.object.select_all(action = "DESELECT")
        object = context.active_object
        lines = object.data.body.split("\n")
        if len(lines) > 1:
            for i, line in enumerate(lines):
                text_data = object.data.copy()
                text_data.body = line
                text_object = bpy.data.objects.new(name = line, object_data = text_data)
                text_object.location = [0, -i, 0]
                text_object.select = True
                context.scene.objects.link(text_object)
            context.scene.objects.unlink(object)
        return {"FINISHED"}
    
                               
                        
    
# properties    

class ObjectFinderProperties(bpy.types.PropertyGroup):
    object_name = StringProperty(name = "Object Name", default = "")
    identifier = IntProperty(name = "Identifier", default = 0)
        
class TargetProperties(bpy.types.PropertyGroup):
    object = PointerProperty(name = "Object", type = ObjectFinderProperties)
    index = IntProperty(name = "Index", default = 0)
    
class MoveProperties(bpy.types.PropertyGroup):
    load = FloatProperty(name = "Load Time", default = 15.0, description = "Time to move from last to this target in frames", min = 0)
    stay = FloatProperty(name = "Stay Time", default = 10.0, description = "Time to stay at this targets in frames", min = 0)
    
class MocamProperties(bpy.types.PropertyGroup):
    active = BoolProperty(name = "Active", default = False)
    targets = CollectionProperty(name = "Targets", type = TargetProperties)
    moves = CollectionProperty(name = "Moves", type = MoveProperties)
    
class MocamObjectProperties(bpy.types.PropertyGroup):
    identifier = IntProperty(name = "Identifier", default = 0)      
    
    
def get_camera_name_items(self, context):
    camera_names = get_camera_names()
    items = []
    for name in camera_names:
        items.append((name, name, ""))
    return items          
    
class MocamSceneProperties(bpy.types.PropertyGroup):
    selected_camera_name = EnumProperty(name = "Camera Name", items = get_camera_name_items)   
    enable_renaming = BoolProperty(name = "Enable Renaming", default = False, description = "Enable renaming mode for all targets")
        
        
def register():
    bpy.utils.register_module(__name__)
    bpy.types.Camera.mocam = PointerProperty(name = "Mocam", type = MocamProperties)
    bpy.types.Object.mocam = PointerProperty(name = "Mocam", type = MocamObjectProperties)
    bpy.types.Scene.mocam = PointerProperty(name = "Mocam", type = MocamSceneProperties)
    
    bpy.app.handlers.scene_update_post.clear()
    bpy.app.handlers.scene_update_post.append(correct_target_lists)

def unregister():
    bpy.utils.unregister_module(__name__)
    
if __name__ == "__main__":
    register()