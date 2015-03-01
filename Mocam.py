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
        for item in self.props.targets:
            if item.index == index:
                return Target(item)
        
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
        
        camera = get_selected_camera()    
        if not camera:
            return
        
        mocam = Mocam(camera)
        
        layout.prop(mocam.properties, "active", text = "Is Camera Active")
        
        targets = mocam.get_targets()
        col = layout.column(align = True)
        for target in targets:
            row = col.row(align = True)
            if scene.mocam.enable_renaming:
                row.prop(target.object, "name", text = "")
            else:
                operator = row.operator("mocam.goto_index", text = target.object.name)
                operator.index = target.index
        
        if mocam.active:
            layout.operator("mocam.add_targets")
            
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
    bl_description = ""
    bl_options = {"REGISTER"}
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def execute(self, context):
        mocam = get_selected_mocam()
        if mocam:
            for object in context.selected_objects:
                if object != camera:
                    mocam.add_target(object)
        return {"FINISHED"}
    
    
class GotoIndex(bpy.types.Operator):
    bl_idname = "mocam.goto_index"
    bl_label = "Goto Index"
    bl_description = ""
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
    enable_renaming = BoolProperty(name = "Enable Renaming", default = False)
        
        
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