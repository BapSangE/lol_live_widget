use serde::{Deserialize, Serialize};
use std::io::Write;
use tauri::Manager;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct Settings {
    pub schema_version: u8,
    pub opacity_percent: u8,
    pub font_scale_percent: u8,
    pub brighten_on_hover: bool,
    pub event_display_seconds: u8,
    pub preferred_match_id: Option<String>,
    pub important_types: Vec<String>,
    pub always_on_top: bool,
    pub launch_at_login: bool,
    pub theme: String,
    pub widget_position: Option<Position>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Position { pub monitor_key: Option<String>, pub x: f64, pub y: f64, #[serde(default="compact")] pub anchor: String }
fn compact()->String { "compact".into() }
impl Default for Settings {
 fn default()->Self {Self {schema_version:1,opacity_percent:65,font_scale_percent:100,brighten_on_hover:false,event_display_seconds:6,preferred_match_id:None,important_types:vec!["GAME_END","BARON","ELDER","GOLD_LEAD_CHANGE","DRAGON_SOUL","MULTIKILL_WINDOW","DRAGON","TOWER"].into_iter().map(String::from).collect(),always_on_top:true,launch_at_login:false,theme:"light".into(),widget_position:None}}
}
impl Settings {
 pub fn validate(&self)->Result<(),String>{
  if self.schema_version!=1{return Err("Unsupported settings version".into());}
  if !(10..=100).contains(&self.opacity_percent)||self.opacity_percent%5!=0{return Err("Invalid opacity".into());}
  if ![100,120,140].contains(&self.font_scale_percent){return Err("Invalid font size".into());}
  if !(3..=15).contains(&self.event_display_seconds){return Err("Invalid event duration".into());}
  if !["light","dark","system"].contains(&self.theme.as_str()){return Err("Invalid theme".into());}
  if self.important_types.iter().any(|t|!["GAME_END","BARON","ELDER","GOLD_LEAD_CHANGE","DRAGON_SOUL","MULTIKILL_WINDOW","DRAGON","TOWER","KILL_DELTA"].contains(&t.as_str())){return Err("Unknown event filter".into());}
  if let Some(p)=&self.widget_position {if !p.x.is_finite()||!p.y.is_finite()||p.anchor!="compact" {return Err("Invalid position".into());}}
  Ok(())
 }
}
#[tauri::command]
pub fn read_settings(app:tauri::AppHandle)->Settings {
 let value=(||->Result<Settings,Box<dyn std::error::Error>>{let path=app.path().app_config_dir()?.join("settings.json");let settings:Settings=serde_json::from_slice(&std::fs::read(path)?)?;settings.validate()?;Ok(settings)})();
 match value {Ok(settings)=>settings,Err(error)=>{eprintln!("Settings restored to defaults: {error}");Settings::default()}}
}
#[tauri::command]
pub fn save_settings(app:tauri::AppHandle,settings:Settings)->Result<(),String>{
 settings.validate()?;
 let folder=app.path().app_config_dir().map_err(|e|e.to_string())?;
 std::fs::create_dir_all(&folder).map_err(|e|e.to_string())?;
 let mut file=tempfile::NamedTempFile::new_in(&folder).map_err(|e|e.to_string())?;
 file.write_all(&serde_json::to_vec_pretty(&settings).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
 file.as_file().sync_all().map_err(|e|e.to_string())?;
 file.persist(folder.join("settings.json")).map_err(|e|e.to_string())?;
 Ok(())
}
#[cfg(test)]
mod tests {
 use super::*;
 #[test] fn font_size_migrates_and_validates() {
  let older:Settings=serde_json::from_str(r#"{"opacityPercent":35}"#).unwrap();
  let json=serde_json::to_value(&older).unwrap();
  assert_eq!(json["fontScalePercent"],100);
  assert_eq!(older.opacity_percent,35);
  for size in [100,120,140] {
   let settings:Settings=serde_json::from_value(serde_json::json!({"fontScalePercent":size})).unwrap();
   assert!(settings.validate().is_ok());
   assert_eq!(serde_json::to_value(settings).unwrap()["fontScalePercent"],size);
  }
  let invalid:Settings=serde_json::from_str(r#"{"fontScalePercent":110}"#).unwrap();
  assert!(invalid.validate().is_err());
 }
 #[test] fn rejects_bad_settings(){let s=Settings{opacity_percent:3,..Settings::default()};assert!(s.validate().is_err());}
 #[test] fn older_v1_without_anchor_migrates(){let s:Settings=serde_json::from_str(r#"{"widgetPosition":{"monitorKey":"screen","x":30,"y":20}}"#).unwrap();assert_eq!(s.widget_position.as_ref().unwrap().anchor,"compact");assert!(s.validate().is_ok());}
}
