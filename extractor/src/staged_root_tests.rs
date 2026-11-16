use super::resolve_staged_root;
use std::ffi::OsString;
use std::path::PathBuf;

#[test]
fn env_root_is_transported_as_exact_os_string() {
    for value in [
        r"C:",
        r"C:\",
        r"C:\stage\",
        r"C:\stage\\",
        r"relative\path",
        r"\\server\share\",
        r"\\?\C:\stage\",
        r"\\?\UNC\server\share\",
        r"C:\sp ace & (x) ! % ^\雪\",
    ] {
        let value = OsString::from(value);
        let root = resolve_staged_root(None, true, Some(value.clone()))
            .unwrap()
            .unwrap();
        assert_eq!(root.as_os_str(), value.as_os_str());
    }
}

#[cfg(windows)]
#[test]
fn env_root_preserves_unpaired_utf16() {
    use std::os::windows::ffi::{OsStrExt, OsStringExt};
    let units = [b'C' as u16, b':' as u16, b'\\' as u16, 0xd800, b'\\' as u16];
    let value = OsString::from_wide(&units);
    let root = resolve_staged_root(None, true, Some(value))
        .unwrap()
        .unwrap();
    assert_eq!(root.as_os_str().encode_wide().collect::<Vec<_>>(), units);
}

#[cfg(unix)]
#[test]
fn env_root_preserves_non_unicode_os_bytes() {
    use std::os::unix::ffi::{OsStrExt, OsStringExt};
    let value = OsString::from_vec(b"/stage/\xff\\".to_vec());
    let root = resolve_staged_root(None, true, Some(value.clone()))
        .unwrap()
        .unwrap();
    assert_eq!(root.as_os_str().as_bytes(), value.as_bytes());
}

#[test]
fn env_root_requires_present_nonempty_value_and_rejects_conflict() {
    assert!(resolve_staged_root(None, true, None).is_err());
    assert!(resolve_staged_root(None, true, Some(OsString::new())).is_err());
    assert!(
        resolve_staged_root(
            Some(PathBuf::from("explicit")),
            true,
            Some(OsString::from("env"))
        )
        .is_err()
    );
}

#[test]
fn flagless_ignores_injected_environment_and_keeps_explicit_root() {
    assert_eq!(
        resolve_staged_root(None, false, Some(OsString::from("env"))).unwrap(),
        None
    );
    let root = resolve_staged_root(
        Some(PathBuf::from("explicit")),
        false,
        Some(OsString::from("env")),
    )
    .unwrap()
    .unwrap();
    assert_eq!(root.as_os_str(), OsString::from("explicit").as_os_str());
}
