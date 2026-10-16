#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

mod macos_server;
mod portable;
mod settings;
mod tray;
mod window_commands;

fn main() {
    let app = tauri::Builder::default()
        .manage(macos_server::Collector::default())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            None,
        ))
        .invoke_handler(tauri::generate_handler![
            settings::read_settings,
            settings::save_settings,
            window_commands::set_window_opacity,
            window_commands::opacity_backend,
            window_commands::quit_app,
            tray::apply_always_on_top,
            portable::local_server_url,
            portable::set_portable_autostart
        ])
        .setup(|app| {
            #[cfg(all(target_os = "macos", feature = "macos-portable"))]
            app.state::<macos_server::Collector>()
                .start(&app.path().resource_dir()?)?;
            tray::install(app)?;
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .build(tauri::generate_context!())
        .expect("Failed to build LoL Live Widget");

    app.run(|app, event| {
        if matches!(event, tauri::RunEvent::Exit) {
            app.state::<macos_server::Collector>().stop();
        }
    });
}
