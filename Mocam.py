import bpy
from bpy.props import *

def get_cameras():
    return [object for object in bpy.context.scene.objects if object.type == "CAMERA"]

class MocamPanel(bpy.types.Panel):
    bl_idname = "MocamPanel"
    bl_label = "Mocam"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Tools"
    
    def draw(self, context):
        layout = self.layout
        
        
class MocamProperties(bpy.types.PropertyGroup):
    active = BoolProperty(name = "Active", default = False)       
        
        
def register():
    bpy.utils.register_module(__name__)
    bpy.types.Camera.mocam = PointerProperty(name = "Mocam", type = MocamProperties)

def unregister():
    bpy.utils.unregister_module(__name__)
    
if __name__ == "__main__":
    register()