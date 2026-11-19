extends Node

var address := "http://127.0.0.1:8782"

func request(path: String, body: Variant = null) -> Dictionary:
	var transport := HTTPRequest.new()
	transport.timeout = 20
	add_child(transport)
	var method := HTTPClient.METHOD_GET if body == null else HTTPClient.METHOD_POST
	var payload := "" if body == null else JSON.stringify(body)
	var error := transport.request(address + path, ["Content-Type: application/json"], method, payload)
	if error != OK:
		transport.queue_free()
		return {"error": "无法发出请求。"}
	var response: Array = await transport.request_completed
	transport.queue_free()
	var status: int = response[1]
	if response[0] != HTTPRequest.RESULT_SUCCESS:
		return {"error": "无法连接对局服务。请确认桌面启动器正在运行。", "status": status}
	var data: Variant = JSON.parse_string(response[3].get_string_from_utf8())
	if not data is Dictionary:
		return {"error": "对局服务返回的内容无法读取。", "status": status}
	if status >= 400:
		return {"error": data.get("error", "操作未完成。"), "status": status}
	return data
