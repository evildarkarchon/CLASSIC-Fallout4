#pragma once

#include <QDialog>
#include <QLineEdit>

/// First-run dialog shown when game or documents paths are not detected.
///
/// Uses classic::scangame::needs_path_detection() to determine which
/// paths are missing, then presents QLineEdit + Browse fields for the
/// user to fill in. Results are saved to CLASSIC Settings.yaml on OK.
class ManualPathDialog : public QDialog {
    Q_OBJECT

public:
    /// Construct the dialog. Pass empty strings for paths that are not
    /// yet known; the dialog will show input fields for those.
    explicit ManualPathDialog(bool needsGamePath,
                              bool needsDocsPath,
                              QWidget* parent = nullptr);

    /// Returns the user-entered game folder path (empty if not needed).
    QString gamePath() const;

    /// Returns the user-entered documents/INI path (empty if not needed).
    QString docsPath() const;

private slots:
    void onBrowseGamePath();
    void onBrowseDocsPath();

private:
    QLineEdit* m_editGamePath = nullptr;
    QLineEdit* m_editDocsPath = nullptr;
};
