#[tauri::command]
pub fn opacity_backend()->&'static str {
 if cfg!(windows)&&std::env::var("LOL_WIDGET_NATIVE_ALPHA").as_deref()==Ok("1"){"native"}else{"css"}
}
pub fn alpha(percent:u8)->Result<u8,String>{
 if !(10..=100).contains(&percent){return Err("Opacity must be 10..100".into());}
 Ok(((255u32*percent as u32+50)/100) as u8)
}
#[tauri::command]
pub fn set_window_opacity(window:tauri::WebviewWindow,percent:u8)->Result<(),String>{
 let value=alpha(percent)?;
 #[cfg(windows)] {
  use windows::Win32::UI::WindowsAndMessaging::{GetWindowLongPtrW,SetWindowLongPtrW,SetLayeredWindowAttributes,GWL_EXSTYLE,WS_EX_LAYERED,LWA_ALPHA};
  use windows::Win32::Foundation::{HWND,COLORREF};
  let handle=window.hwnd().map_err(|e|e.to_string())?;
  let hwnd=HWND(handle.0 as _);
  unsafe {
   let original=GetWindowLongPtrW(hwnd,GWL_EXSTYLE);
   SetWindowLongPtrW(hwnd,GWL_EXSTYLE,original|WS_EX_LAYERED.0 as isize);
   if let Err(error)=SetLayeredWindowAttributes(hwnd,COLORREF(0),value,LWA_ALPHA){
    SetWindowLongPtrW(hwnd,GWL_EXSTYLE,original);
    eprintln!("SetLayeredWindowAttributes failed: {error}");
    return Err(error.to_string());
   }
  }
  Ok(())
 }
 #[cfg(not(windows))] {let _=(window,value);Err("Native window opacity requires Windows".into())}
}
#[cfg(test)]
mod tests {
 use super::*;
 #[test] fn alpha_values(){assert_eq!(alpha(10).unwrap(),26);assert_eq!(alpha(65).unwrap(),166);assert_eq!(alpha(100).unwrap(),255);assert!(alpha(9).is_err());assert!(alpha(101).is_err());}
}
