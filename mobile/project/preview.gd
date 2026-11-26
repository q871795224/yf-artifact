extends Node
func _ready() -> void:
	if "--still" in OS.get_cmdline_user_args():
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		get_tree().quit(get_viewport().get_texture().get_image().save_png(OS.get_cmdline_user_args()[-1]))
