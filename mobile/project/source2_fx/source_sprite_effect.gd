extends Node3D

# These two Source systems emit stationary, single-frame sprites at control point 0.
# The parent supplies the card-plane transform and seeks the effect in seconds.
@export var color_override := Color.TRANSPARENT
@export var unit_scale := 0.12

func _ready() -> void:
	var layer := 0
	for sprite: MeshInstance3D in get_children():
		var p: Dictionary = sprite.get_meta("params")
		var mat := StandardMaterial3D.new()
		mat.resource_local_to_scene = true
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD if p.additive else BaseMaterial3D.BLEND_MODE_MIX
		mat.cull_mode = BaseMaterial3D.CULL_DISABLED
		mat.render_priority = 10 + layer
		mat.albedo_texture = sprite.get_meta("texture")
		sprite.mesh = QuadMesh.new()
		sprite.material_override = mat
		sprite.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		sprite.rotation.z = deg_to_rad(p.angle)
		layer += 1
	seek(-1)

func seek(time: float) -> void:
	for sprite: MeshInstance3D in get_children():
		var p: Dictionary = sprite.get_meta("params")
		var age: float = time - p.start
		sprite.visible = age >= 0 and age < p.life
		if not sprite.visible:
			continue
		var t := clampf(age / (p.life * p.size_end), 0, 1)
		var diameter := 2 * unit_scale * float(p.radius) * lerpf(p.size_from, 1, pow(t, log(p.bias) / log(0.5)))
		sprite.scale = Vector3.ONE * diameter
		var alpha := minf(1, age / maxf(p.fade_in, 0.00001)) if p.fade_in > 0 else 1.0
		alpha *= minf(1, (p.life - age) / maxf(p.fade_out, 0.00001))
		var c: Array = p.color
		var color := Color8(int(c[0]), int(c[1]), int(c[2]), int(c[3]))
		if color_override.a > 0.0:
			color = Color(color_override, color.a)
		color.a *= alpha
		var mat := sprite.material_override as StandardMaterial3D
		mat.albedo_color = Color(color.r*p.brightness, color.g*p.brightness, color.b*p.brightness, color.a)
