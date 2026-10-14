#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod settings;
mod tray;
mod window_commands;
fn main(){
 tauri::Builder::default()
  .plugin(tauri_plugin_autostart::init(tauri_plugin_autostart::MacosLauncher::LaunchAgent,None))
  .invoke_handler(tauri::generate_handler![settings::read_settings,settings::save_settings,window_commands::set_window_opacity,window_commands::opacity_backend,tray::apply_always_on_top])
  .setup(|app|{tray::install(app)?;Ok(())})
  .on_window_event(|window,event|{if let tauri::WindowEvent::CloseRequested{api,..}=event{api.prevent_close();let _=window.hide();}})
  .run(tauri::generate_context!()).expect("Failed to run LoL Live Widget");
}
