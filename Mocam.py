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
from bpy.app.handlers import persistent
from bpy.props import *
from operator import attrgetter

@persistent
def correct_target_lists(scene):
    for mocam in get_active_mocams():
        mocam.correct_target_list()

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
        
    @property
    def active(self):
        return self.props.active
    @active.setter
    def active(self, active):
        self.props.active = active
        
    @property
    def properties(self):
        return self.props
    
    
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
    
    def __getitem__(self, key):
        return self.targets[key]
    
    def __len__(self):
        return len(self.targets)
    
    
class Target:
    def __init__(self, target_item):
        self.object = ObjectFinder.get_object(target_item.object)
        self.index = target_item.index    



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
                operator = row.operator("mocam.goto_index", text = "", icon = "EYEDROPPER")
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
                    
                operator = row.operator("mocam.goto_index", text = target.object.name)
                operator.index = target.index
                    
                operator = row.operator("mocam.remove_target", text = "", icon = "X")
                operator.index = target.index
        
        if mocam.active:
            layout.operator("mocam.add_targets", text = "Add Targets from Selection", icon = "PLUS")
            
        layout.prop(scene.mocam, "enable_renaming")
            
     
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
    
    
class GotoIndex(bpy.types.Operator):
    bl_idname = "mocam.goto_index"
    bl_label = "Goto Index"
    bl_description = "Jump to this target"
    bl_options = {"REGISTER"}
    
    index = IntProperty(name = "Index", default = 0)
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        mocam = get_selected_mocam()
        if mocam:
            target = mocam.get_target_from_index(self.index)
            if target:
                bpy.ops.object.select_all(action = "DESELECT")
                target.object.select = True
                context.scene.objects.active = target.object
        return {"FINISHED"}
            
            
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
        return True
    
    def execute(self, context):
        mocam = get_selected_mocam()
        if mocam:
            mocam.change_indices(self.index_from, self.index_to)
        return {"FINISHED"}
                     
                        
    
# properties    

class ObjectFinderProperties(bpy.types.PropertyGroup):
    object_name = StringProperty(name = "Object Name", default = "")
    identifier = IntProperty(name = "Identifier", default = 0)
        
class TargetProperties(bpy.types.PropertyGroup):
    object = PointerProperty(name = "Object", type = ObjectFinderProperties)
    index = IntProperty(name = "Index", default = 0)
    
class MocamProperties(bpy.types.PropertyGroup):
    active = BoolProperty(name = "Active", default = False)
    targets = CollectionProperty(name = "Targets", type = TargetProperties)    
    
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