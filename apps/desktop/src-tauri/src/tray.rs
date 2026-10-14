use tauri::{Emitter,Manager,menu::{Menu,MenuItem,CheckMenuItem},tray::TrayIconBuilder};
use std::sync::Mutex;
pub struct TopMenu(pub Mutex<CheckMenuItem<tauri::Wry>>);
#[tauri::command]
pub fn apply_always_on_top(app:tauri::AppHandle,enabled:bool)->Result<(),String>{
 if let Some(window)=app.get_webview_window("main"){window.set_always_on_top(enabled).map_err(|e|e.to_string())?;}
 app.state::<TopMenu>().0.lock().map_err(|e|e.to_string())?.set_checked(enabled).map_err(|e|e.to_string())?;
 Ok(())
}
pub fn install(app:&tauri::App)->tauri::Result<()> {
 let show=MenuItem::with_id(app,"show","보이기/숨기기",true,None::<&str>)?;
 let matches=MenuItem::with_id(app,"matches","경기 선택",true,None::<&str>)?;
 let top=CheckMenuItem::with_id(app,"top","항상 위",true,crate::settings::read_settings(app.handle().clone()).always_on_top,None::<&str>)?;
 let settings=MenuItem::with_id(app,"settings","설정",true,None::<&str>)?;
 let exit=MenuItem::with_id(app,"exit","종료",true,None::<&str>)?;
 let menu=Menu::with_items(app,&[&show,&matches,&top,&settings,&exit])?;
 app.manage(TopMenu(Mutex::new(top)));
 TrayIconBuilder::new().icon(tauri::image::Image::from_bytes(include_bytes!("../icons/icon.png"))?).tooltip("LoL Live Widget").menu(&menu).show_menu_on_left_click(true).on_menu_event(|app,event|{
  let Some(window)=app.get_webview_window("main") else{return;};
  match event.id.as_ref(){
   "exit"=>app.exit(0),
   "show"=>{if window.is_visible().unwrap_or(false){let _=window.hide();}else{let _=window.show();let _=window.set_focus();}},
   "settings"|"matches"=>{let _=window.show();let _=window.set_focus();let _=app.emit("open-settings",event.id.as_ref());},
   "top"=>{let enabled=app.state::<TopMenu>().0.lock().ok().and_then(|m|m.is_checked().ok()).unwrap_or(true);let _=apply_always_on_top(app.clone(),enabled);let _=app.emit("always-on-top-changed",enabled);},
   _=>{}
  }
 }).build(app)?;
 Ok(())
}
