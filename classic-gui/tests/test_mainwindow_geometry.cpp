#include <QFile>
#include <QRegularExpression>
#include <QtTest/QtTest>

class MainWindowGeometryTests : public QObject {
    Q_OBJECT

private slots:
    void main_tab_minimum_geometry_constant_matches_default_layout();
    void tab_bar_configuration_is_responsive_for_narrow_windows();
    void custom_folder_handlers_refresh_results_directories();
    void crash_scan_status_bar_tracks_scan_statistics();
};

void MainWindowGeometryTests::main_tab_minimum_geometry_constant_matches_default_layout()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.h");
    QFile file(headerPath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(file.readAll());
    const QRegularExpression entryRegex(
        QStringLiteral(R"(\{\s*(\d+)\s*,\s*(\d+)\s*\},\s*//\s*Main Options)"));
    const QRegularExpressionMatch match = entryRegex.match(headerText);
    QVERIFY2(match.hasMatch(), "Main Options tab minimum geometry entry not found");

    QCOMPARE(match.captured(1).toInt(), 640);
    QCOMPARE(match.captured(2).toInt(), 500);
}

void MainWindowGeometryTests::tab_bar_configuration_is_responsive_for_narrow_windows()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    QVERIFY2(sourceText.contains(QStringLiteral("setElideMode(Qt::ElideRight)")),
             "Expected tab bar elide mode configuration was not found");
    QVERIFY2(sourceText.contains(QStringLiteral("setExpanding(true)")),
             "Expected tab bar expanding configuration was not found");
}

void MainWindowGeometryTests::custom_folder_handlers_refresh_results_directories()
{
    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile file(sourcePath);
    QVERIFY2(file.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(file.readAll());

    const auto extractFunctionBody = [&](const QString& signature) -> QString {
        const QString marker = QStringLiteral("void MainWindow::") + signature;
        const qsizetype start = sourceText.indexOf(marker);
        if (start < 0) {
            return {};
        }

        const qsizetype nextFunction = sourceText.indexOf(
            QStringLiteral("\nvoid MainWindow::"), start + marker.size());
        const qsizetype end = (nextFunction < 0) ? sourceText.size() : nextFunction;
        return sourceText.mid(start, end - start);
    };

    const QString browseBody = extractFunctionBody(QStringLiteral("onBrowseCustom()"));
    QVERIFY2(!browseBody.isEmpty(), "Could not locate MainWindow::onBrowseCustom()");
    QVERIFY2(
        browseBody.contains(QStringLiteral("initResultsReportDir();")),
        "onBrowseCustom should refresh Results report directories after updating custom path");

    const QString editedBody = extractFunctionBody(QStringLiteral("onCustomFolderEdited()"));
    QVERIFY2(!editedBody.isEmpty(), "Could not locate MainWindow::onCustomFolderEdited()");
    QVERIFY2(
        editedBody.contains(QStringLiteral("initResultsReportDir();")),
        "onCustomFolderEdited should refresh Results report directories after updating custom path");
}

void MainWindowGeometryTests::crash_scan_status_bar_tracks_scan_statistics()
{
    const QString headerPath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.h");
    QFile headerFile(headerPath);
    QVERIFY2(headerFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(headerPath)));

    const QString headerText = QString::fromUtf8(headerFile.readAll());
    QVERIFY2(headerText.contains(QStringLiteral("QElapsedTimer m_crashScanTimer")),
             "MainWindow should keep a crash-scan elapsed timer for status updates");
    QVERIFY2(headerText.contains(QStringLiteral("int m_crashScanLogsCompleted")),
             "MainWindow should track completed crash-log count for status updates");
    QVERIFY2(headerText.contains(QStringLiteral("int m_crashScanTotalLogs")),
             "MainWindow should track total crash-log count for status updates");

    const QString sourcePath = QStringLiteral(QT_TESTCASE_SOURCEDIR "/../src/app/mainwindow.cpp");
    QFile sourceFile(sourcePath);
    QVERIFY2(sourceFile.open(QIODevice::ReadOnly | QIODevice::Text),
             qPrintable(QStringLiteral("Unable to read %1").arg(sourcePath)));

    const QString sourceText = QString::fromUtf8(sourceFile.readAll());
    QVERIFY2(sourceText.contains(QStringLiteral("logs scanned")),
             "Crash scan status text should include scanned-log statistics");
    QVERIFY2(sourceText.contains(QStringLiteral("elapsed")),
             "Crash scan status text should include elapsed time statistics");
    QVERIFY2(sourceText.contains(QStringLiteral("progressCompletedEstimate")),
             "Crash scan status should derive scanned-log stats from streaming progress updates");
}

QTEST_MAIN(MainWindowGeometryTests)
#include "test_mainwindow_geometry.moc"
