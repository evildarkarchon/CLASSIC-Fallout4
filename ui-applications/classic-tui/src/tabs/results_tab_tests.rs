use super::{MarkdownLink, collect_visible_link_hit_areas};
use ratatui::layout::Rect;

fn link(line_index: usize, start_col: usize, end_col: usize) -> MarkdownLink {
    MarkdownLink {
        index: 7,
        line_index,
        start_col,
        end_col,
        url: "https://example.com".to_string(),
        label: "example".to_string(),
    }
}

#[test]
fn visible_link_hit_area_maps_markdown_position_to_viewport_rect() {
    let text_area = Rect::new(10, 5, 40, 8);
    let hits = collect_visible_link_hit_areas(text_area, 10, &[link(12, 3, 11)]);

    assert_eq!(hits.len(), 1);
    assert_eq!(hits[0].link_index, 7);
    assert_eq!(hits[0].area, Rect::new(13, 7, 8, 1));
}

#[test]
fn visible_link_hit_area_clips_offscreen_and_zero_width_links() {
    let text_area = Rect::new(0, 0, 10, 3);
    let links = [
        link(1, 2, 6),
        link(0, 1, 5),
        link(4, 1, 5),
        link(1, 12, 14),
        link(2, 8, 20),
    ];
    let hits = collect_visible_link_hit_areas(text_area, 1, &links);

    assert_eq!(hits.len(), 2);
    assert_eq!(hits[0].area, Rect::new(2, 0, 4, 1));
    assert_eq!(hits[1].area, Rect::new(8, 1, 2, 1));
}
