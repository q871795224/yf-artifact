extends Node

var bridge: Variant
var apk_path := ""
var pipe := {}
var thread := Thread.new()

func request(message: Dictionary) -> Dictionary:
	message.storage = ProjectSettings.globalize_path("user://")
	var data := JSON.stringify(message)
	var reply := ""
	if OS.get_name() == "Android":
		if bridge == null:
			bridge = Engine.get_singleton("JavaClassWrapper").wrap("org.yfartifact.match.OfflineRules")
			apk_path = Engine.get_singleton("AndroidRuntime").getActivity().getPackageCodePath()
		if bridge == null or not bridge.submit(apk_path, message.storage, data):
			return {"error":"离线规则未能启动"}
		while reply.is_empty():
			await get_tree().process_frame
			reply = bridge.poll()
	else:
		if pipe.is_empty():
			var script := OS.get_environment("YF_MATCH_RULES")
			if script.is_empty():
				return {"error":"桌面调试需要设置 YF_MATCH_RULES 指向 mobile/yf_match.py。"}
			pipe = OS.execute_with_pipe("python3", PackedStringArray(["-u",script]), true)
		if not pipe.has("stdio"):
			return {"error":"Python 未能启动"}
		thread.start(exchange.bind(data))
		while thread.is_alive():
			await get_tree().process_frame
		reply = thread.wait_to_finish()
	var parsed: Variant = JSON.parse_string(reply)
	return parsed if parsed is Dictionary else {"error":"无法读取对局结果，请返回后继续对局。"}

func exchange(data: String) -> String:
	var io: FileAccess = pipe.stdio
	io.store_line(data)
	io.flush()
	return io.get_line()

func _exit_tree() -> void:
	if pipe.has("pid"):
		OS.kill(pipe.pid)
	if thread.is_started():
		thread.wait_to_finish()
