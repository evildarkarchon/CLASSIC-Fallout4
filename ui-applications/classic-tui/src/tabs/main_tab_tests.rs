use super::MainFocus;

#[test]
fn main_focus_next_wraps_to_start() {
    let mut focus = MainFocus::StagingInput;
    for _ in 0..11 {
        focus = focus.next();
    }
    assert_eq!(focus.next(), MainFocus::StagingInput);
}

#[test]
fn main_focus_prev_wraps_to_end() {
    assert_eq!(MainFocus::StagingInput.prev(), MainFocus::Papyrus);
}
