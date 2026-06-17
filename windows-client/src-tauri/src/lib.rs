// Tauri entry: 个人 AI 知识库

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|_app| {
            // 启动钩子：可在这里初始化系统托盘、全局快捷键等
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
