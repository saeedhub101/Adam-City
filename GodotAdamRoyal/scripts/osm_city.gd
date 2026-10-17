extends Node3D

const DATA_PATH := "res://assets/manila_city.json"
var building_count := 0
var road_count := 0

func load_city() -> Dictionary:
	if not FileAccess.file_exists(DATA_PATH):
		push_error("Missing real Manila OSM dataset: " + DATA_PATH)
		return {"ok": false, "buildings": 0, "roads": 0}
	var file := FileAccess.open(DATA_PATH, FileAccess.READ)
	if file == null:
		return {"ok": false, "buildings": 0, "roads": 0}
	var parsed = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("Manila OSM dataset is not valid JSON")
		return {"ok": false, "buildings": 0, "roads": 0}
	var buildings: Array = parsed.get("buildings", [])
	var roads: Array = parsed.get("roads", [])
	building_count = buildings.size()
	road_count = roads.size()
	_build_roads(roads)
	_build_buildings(buildings)
	return {"ok": building_count > 0 and road_count > 0, "buildings": building_count, "roads": road_count}

func _build_roads(roads: Array) -> void:
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	var any_vertices := false
	for road in roads:
		var points: Array = road.get("points", [])
		if points.size() < 2:
			continue
		var width := float(road.get("width", 5.0))
		for i in range(points.size() - 1):
			var a: Vector3 = _point(points[i], 0.025)
			var b: Vector3 = _point(points[i + 1], 0.025)
			var segment := Vector2(b.x - a.x, b.z - a.z)
			if segment.length() < 0.05:
				continue
			var side := Vector3(-segment.y, 0, segment.x).normalized() * width * 0.5
			var color := Color(0.16, 0.18, 0.19)
			tool.set_color(color); tool.add_vertex(a - side)
			tool.set_color(color); tool.add_vertex(a + side)
			tool.set_color(color); tool.add_vertex(b + side)
			tool.set_color(color); tool.add_vertex(a - side)
			tool.set_color(color); tool.add_vertex(b + side)
			tool.set_color(color); tool.add_vertex(b - side)
			any_vertices = true
	if any_vertices:
		tool.generate_normals()
		var mesh := tool.commit()
		var material := StandardMaterial3D.new()
		material.vertex_color_use_as_albedo = true
		material.roughness = 0.96
		mesh.surface_set_material(0, material)
		var instance := MeshInstance3D.new()
		instance.name = "OSM_Road_Network"
		instance.mesh = mesh
		add_child(instance)

func _build_buildings(buildings: Array) -> void:
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	var any_vertices := false
	for building in buildings:
		var footprint: Array = building.get("points", [])
		if footprint.size() < 3:
			continue
		var height := clamp(float(building.get("height", 8.0)), 3.0, 100.0)
		var seed_value := int(building.get("id", 1)) % 13
		var base := Color(0.48 + float(seed_value % 4) * 0.045, 0.45 + float(seed_value % 5) * 0.035, 0.39 + float(seed_value % 3) * 0.04)
		var roof := base.lightened(0.18)
		var pts: Array[Vector3] = []
		for p in footprint:
			pts.append(_point(p, 0.0))
		for i in range(pts.size()):
			var j := (i + 1) % pts.size()
			var bottom_a := pts[i]
			var bottom_b := pts[j]
			var top_a := bottom_a + Vector3.UP * height
			var top_b := bottom_b + Vector3.UP * height
			tool.set_color(base); tool.add_vertex(bottom_a)
			tool.set_color(base); tool.add_vertex(bottom_b)
			tool.set_color(base.darkened(0.08)); tool.add_vertex(top_b)
			tool.set_color(base); tool.add_vertex(bottom_a)
			tool.set_color(base.darkened(0.08)); tool.add_vertex(top_b)
			tool.set_color(base.darkened(0.05)); tool.add_vertex(top_a)
			any_vertices = true
		for i in range(1, pts.size() - 1):
			tool.set_color(roof); tool.add_vertex(pts[0] + Vector3.UP * height)
			tool.set_color(roof); tool.add_vertex(pts[i] + Vector3.UP * height)
			tool.set_color(roof); tool.add_vertex(pts[i + 1] + Vector3.UP * height)
	if any_vertices:
		tool.generate_normals()
		var mesh := tool.commit()
		var material := StandardMaterial3D.new()
		material.vertex_color_use_as_albedo = true
		material.roughness = 0.9
		mesh.surface_set_material(0, material)
		var instance := MeshInstance3D.new()
		instance.name = "OSM_Building_Footprints"
		instance.mesh = mesh
		add_child(instance)

func _point(value: Array, y: float) -> Vector3:
	return Vector3(float(value[0]), y, float(value[1]))
