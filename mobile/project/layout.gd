extends Node3D
const EMPTY_CELL_SHADER = preload("res://empty_cell.gdshader")
const TOWER_ROWS := [1,6]
const TOWER_COLUMN := 2
const ARENA_TARGET := Vector3(0,0,-0.135)
var tower_bounds: Array[AABB] = []
var cell_paints := {}
var arena_preview := true
var pitch_study := false
var ratio_study := false
var fill_all_cells := true
var cell_ratio := 1.2
var wood_extension := 1.69
var camera_elevation := 58.0
var piece_pitch := 22.0
var compensate_pitch := true
var equipment_preview := 2
var show_samples := true
var show_fountain_rows := true
var card_fill := 1.0
var tower_display_tilt := 28.0
func capture_tower_bounds() -> void:
	for model: Node3D in $Towers.get_children():
		var bounds := AABB()
		var to_model := model.global_transform.affine_inverse()
		for part: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
			if "broken" in part.name:
				part.hide()
				continue
			var mesh_bounds := to_model * part.global_transform * part.get_aabb()
			bounds = bounds.merge(mesh_bounds) if bounds.has_volume() else mesh_bounds
		tower_bounds.append(bounds)

func clear_generated(parent: Node3D) -> void:
	for node in parent.get_children():
		parent.remove_child(node)
		node.queue_free()

func rebuild_samples() -> void:
	clear_generated($LayoutSamples)
	$LayoutSamples.visible = show_samples
	var half_rows := 4 if show_fountain_rows else 3
	# Anchor the outside edges, then distribute the remaining space between rows.
	var inner_edge := 0.124 if arena_preview else 0.054
	var outer_edge := wood_extension + 0.447 - 0.028
	var tile_size := minf(0.338 if arena_preview else 0.322, (outer_edge - inner_edge) / (half_rows + 0.2))
	var half_depth := tile_size * (1.2 if arena_preview else 1.0) * 0.5
	var front := inner_edge + half_depth
	var stride := (outer_edge - half_depth - front) / (half_rows - 1)
	var card_size := tile_size * card_fill
	for team in 2:
		var color := Color("#a86455") if team == 0 else Color("#66a894")
		var direction := -1.0 if team == 0 else 1.0
		for row in half_rows:
			var z := (front + stride * row) * direction
			var board_row := 3 - row if team == 0 else 4 + row
			var tile_color := Color(color, 0.58) if board_row in [0, 7] else Color("#d4c6ac58")
			for col in 5:
				var at := Vector3((col - 2) * 0.345, 0.006, z)
				if board_row == TOWER_ROWS[team] and col == TOWER_COLUMN:
					place_tower(team, board_row, tile_size, at)
					cell_corners(Vector2i(col, board_row), tile_size, at, Color(color.lightened(0.20), 0.82))
				else:
					cell_corners(Vector2i(col, board_row), tile_size, at, tile_color)
					var paired_rows := ratio_study and team == 1 and row < 2
					var occupied := paired_rows or (row == 0 and (col == 2 or (team == 1 and col == 1)))
					if pitch_study:
						occupied = fill_all_cells or col in [1,3]
					if occupied:
						var piece := preload("res://unit_piece.gd").new()
						$LayoutSamples.add_child(piece)
						var hero := col == 3 if pitch_study else team == 1 and col == 2
						var height_ratio := cell_ratio if hero else 1.0
						piece.set_meta("piece_cell", Vector2i(col, board_row))
						piece.build_piece(hero, [[],[1],[0,1,2]][equipment_preview], height_ratio)
						piece.position = at + Vector3.UP * 0.002
						piece.basis = Basis(Vector3.LEFT, Vector3.BACK, Vector3.UP)
						piece.scale = Vector3.ONE * card_size / 0.294
						if piece_pitch > 0:
							var pitch := deg_to_rad(piece_pitch)
							if compensate_pitch:
								var ray := arena_camera_position() - at
								var elevation := atan2(ray.y, -ray.z)
								pitch += deg_to_rad(camera_elevation) - elevation
							piece.rotate_x(-pitch)
							piece.position += Vector3(0,sin(pitch),cos(pitch)-1) * card_size * height_ratio * 0.5

func place_tower(team: int, row: int, tile_size: float, at: Vector3) -> void:
	var model := $Towers.get_child(team) as Node3D
	var bounds := tower_bounds[team]
	model.rotation = Vector3(-deg_to_rad(tower_display_tilt), PI, 0.0)
	model.scale = Vector3.ONE * (tile_size * 0.76 / maxf(bounds.size.x, bounds.size.z))
	var posed := Transform3D(model.basis, Vector3.ZERO) * bounds
	var center := posed.get_center()
	model.position = at + Vector3.UP * (0.008 if arena_preview else 0.023) - Vector3(center.x, posed.position.y, center.z)
	add_tower_pedestal(team, tile_size, at)
	model.set_meta("board_cell", Vector2i(TOWER_COLUMN, row))
	if arena_preview:
		var front := preload("res://unit_piece.gd").new()
		$LayoutSamples.add_child(front)
		front.position = at + Vector3(0,0.025,-tile_size*0.32)
		front.basis = Basis(Vector3.LEFT,Vector3.BACK,Vector3.UP).rotated(Vector3.RIGHT,deg_to_rad(-22))
		front.scale = Vector3.ONE * tile_size / 0.294 * 1.22
		front.add_stat("card_attack",4,Vector3(-0.062,0,0.008))
		front.add_stat("card_health",40,Vector3(0.062,0,0.008))

func add_tower_pedestal(team: int, tile_size: float, at: Vector3) -> void:
	var base := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.radial_segments = 8
	mesh.top_radius = tile_size * 0.39
	mesh.bottom_radius = tile_size * 0.44
	mesh.height = 0.008 if arena_preview else 0.023
	base.mesh = mesh
	var stone := StandardMaterial3D.new()
	stone.albedo_color = Color("#544440") if team == 0 else Color("#606759")
	stone.roughness = 0.90
	base.material_override = stone
	base.position = at + Vector3.UP * mesh.height * 0.5
	if arena_preview:
		base.scale = Vector3(0.94,1,0.80)
		var inlay := ShaderMaterial.new()
		inlay.shader = preload("res://tower_inlay.gdshader")
		inlay.set_shader_parameter("rock",Color("#504341") if team == 0 else Color("#545a4d"))
		inlay.set_shader_parameter("radius",mesh.top_radius)
		base.material_override = inlay
	base.rotation.y = PI / 8.0
	$LayoutSamples.add_child(base)

func cell_corners(cell: Vector2i, size: float, at: Vector3, color: Color) -> void:
	if not cell_paints.has(color):
		var paint := ShaderMaterial.new()
		paint.shader = EMPTY_CELL_SHADER
		paint.set_shader_parameter("tint", color)
		cell_paints[color] = paint
	var marker := card_plane(size, at, Color.WHITE)
	marker.set_meta("cell_marker", cell)
	marker.scale.z = cell_ratio
	marker.material_override = cell_paints[color]

func card_plane(size: float, at: Vector3, color: Color, texture: Texture2D = null) -> MeshInstance3D:
	var mesh := PlaneMesh.new()
	mesh.size = Vector2.ONE * size
	var paint := StandardMaterial3D.new()
	paint.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	if color.a < 1.0:
		paint.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	paint.albedo_color = color
	paint.albedo_texture = texture
	var plane := MeshInstance3D.new()
	plane.mesh = mesh
	plane.material_override = paint
	plane.position = at
	plane.rotation.y = PI if texture != null else 0.0
	plane.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	$LayoutSamples.add_child(plane)
	return plane

func arena_camera_position() -> Vector3:
	var angle := deg_to_rad(camera_elevation)
	return ARENA_TARGET + Vector3(0,sin(angle),-cos(angle))*25.85
