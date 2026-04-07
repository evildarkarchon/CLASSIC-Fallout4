#[cxx::bridge(namespace = "classic::enums")]
mod ffi {
    #[derive(Debug, Clone, Copy)]
    enum SimpleKind {
        A,
        B,
        C,
    }
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum ProgressEventKind {
        Queued = 0,
        Started = 1,
        Completed = 2,
    }
}
