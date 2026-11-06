import bpy
sc = bpy.context.scene
sc.render.use_overwrite = False; sc.render.use_placeholder = True
sc.render.filepath = __import__('os').environ['W'] + '/frames/f_'
bpy.ops.render.render(animation=True)
