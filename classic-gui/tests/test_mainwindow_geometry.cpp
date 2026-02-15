#include <QFile>
#include <QRegularExpression>
#include <QtTest/QtTest>

class MainWindowGeometryTests : public QObject {
    Q_OBJECT

private slots:
    void main_tab_minimum_geometry_constant_matches_default_layout();
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

QTEST_MAIN(MainWindowGeometryTests)
#include "test_mainwindow_geometry.moc"
