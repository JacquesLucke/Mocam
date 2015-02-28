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
from bpy.props import *
from operator import attrgetter

def get_selected_camera():
    cameras = get_cameras()
    if len(cameras) == 0:
        return None
    elif len(cameras) == 1:
        return cameras[0]
    scene = bpy.context.scene
    return scene.objects.get(scene.mocam.selected_camera_name)

def is_camera_active(camera):
    return camera.data.mocam.active
def set_camera_active(camera):
    camera.data.mocam.active = True

def get_camera_names():
    return [camera.name for camera in get_cameras()]
def get_cameras():
    return [object for object in bpy.context.scene.objects if object.type == "CAMERA"]


class Mocam:
    def __init__(self, camera):
        self.camera = camera
        self.props = camera.data.mocam
        
    def add_target(self, object):
        item = self.props.targets.add()
        item.index = 0
        item.key = OPH.get_new_key(default_object = object)
        
    def get_targets(self):
        return TargetList(self.props.targets)
        
    @property
    def active(self):
        return self.props.active
    @active.setter
    def active(self, active):
        self.props.active = active
        
    @property
    def properties(self):
        return self.props
    
    
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
        self.object = OPH.get_object(target_item.key)
        self.index = target_item.index    


class ObjectPropertyHelper:
    helper_object_name = "Mocam Helper"
    
    def get_new_key(self, name = "key", default_object = None):
        object = self.get_helper_object()
        constraint = object.constraints.new(type = "CHILD_OF")
        constraint.influence = 0
        constraint.target = default_object
        return constraint.name
    
    def set_object(self, key, object):
        helper_object = self.get_helper_object()
        constraint = helper_object.constraints.get(key)
        if constraint is None:
            self.get_new_key(name = key)
            constraint = helper_object.constraints.get(key)
        constraint.target = object
    
    def get_object(self, key):
        object = self.get_helper_object()
        constraint = object.constraints.get(key)
        if constraint is None:
            return None
        return constraint.target
        
    def get_helper_object(self):
        object = bpy.data.objects.get(self.helper_object_name)
        if not object:
            object = self.create_helper_object()
        return object
    
    def create_helper_object(self):
        object = bpy.data.objects.new(self.helper_object_name, None)
        bpy.context.scene.objects.link(object)
        object.hide = True
        return object
OPH = ObjectPropertyHelper()    


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
            row.label(target.object.name)
        
        if mocam.active:
            layout.operator("mocam.add_targets")
            
     
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
        set_camera_active(context.active_object)
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
        camera = get_selected_camera()
        if camera:
            mocam = Mocam(camera)
            for object in context.selected_objects:
                mocam.add_target(object)
        return {"FINISHED"}
                        
    
# properties    
        
class TargetProperties(bpy.types.PropertyGroup):
    key = StringProperty(name = "Object Key", default = "")
    index = IntProperty(name = "Index", default = 0)
    
class MocamProperties(bpy.types.PropertyGroup):
    active = BoolProperty(name = "Active", default = False)
    targets = CollectionProperty(name = "Targets", type = TargetProperties)    
    
    
def get_camera_name_items(self, context):
    camera_names = get_camera_names()
    items = []
    for name in camera_names:
        items.append((name, name, ""))
    return items          
    
class MocamSceneProperties(bpy.types.PropertyGroup):
    selected_camera_name = EnumProperty(name = "Camera Name", items = get_camera_name_items)   
        
        
def register():
    bpy.utils.register_module(__name__)
    bpy.types.Camera.mocam = PointerProperty(name = "Mocam", type = MocamProperties)
    bpy.types.Scene.mocam = PointerProperty(name = "Mocam", type = MocamSceneProperties)

def unregister():
    bpy.utils.unregister_module(__name__)
    
if __name__ == "__main__":
    register()