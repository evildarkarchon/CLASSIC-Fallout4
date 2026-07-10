#include "core/gamepathutils.h"

#include <QDir>
#include <QFile>
#include <QTemporaryDir>
#include <QtTest/QtTest>

class GamePathUtilsTests : public QObject {
    Q_OBJECT

private slots:
    void validExecutableUnderRootIsPreserved();
    void executableOutsideRootUsesDefault();
    void missingExecutableUsesDefault();
    void emptyRootLeavesExecutableUnchanged();
};

void GamePathUtilsTests::validExecutableUnderRootIsPreserved()
{
    QTemporaryDir temp;
    QVERIFY(temp.isValid());
    const QString gameRoot = temp.filePath(QStringLiteral("Fallout4"));
    QVERIFY(QDir().mkpath(gameRoot));
    const QString gameExePath = QDir(gameRoot).filePath(QStringLiteral("Fallout4.exe"));
    QFile executable(gameExePath);
    QVERIFY(executable.open(QIODevice::WriteOnly));
    executable.close();

    QCOMPARE(classic::gui::normalizeGameExecutablePath(gameExePath, gameRoot), QDir::cleanPath(gameExePath));
}

void GamePathUtilsTests::executableOutsideRootUsesDefault()
{
    QTemporaryDir temp;
    QVERIFY(temp.isValid());
    const QString gameRoot = temp.filePath(QStringLiteral("Fallout4"));
    const QString otherRoot = temp.filePath(QStringLiteral("Other"));
    QVERIFY(QDir().mkpath(gameRoot));
    QVERIFY(QDir().mkpath(otherRoot));
    const QString otherExePath = QDir(otherRoot).filePath(QStringLiteral("Fallout4.exe"));
    QFile executable(otherExePath);
    QVERIFY(executable.open(QIODevice::WriteOnly));
    executable.close();

    QCOMPARE(classic::gui::normalizeGameExecutablePath(otherExePath, gameRoot),
             QDir(gameRoot).filePath(QStringLiteral("Fallout4.exe")));
}

void GamePathUtilsTests::missingExecutableUsesDefault()
{
    QTemporaryDir temp;
    QVERIFY(temp.isValid());
    const QString gameRoot = temp.filePath(QStringLiteral("Fallout4"));
    QVERIFY(QDir().mkpath(gameRoot));

    QCOMPARE(classic::gui::normalizeGameExecutablePath(temp.filePath(QStringLiteral("missing.exe")), gameRoot),
             QDir(gameRoot).filePath(QStringLiteral("Fallout4.exe")));
}

void GamePathUtilsTests::emptyRootLeavesExecutableUnchanged()
{
    QCOMPARE(classic::gui::normalizeGameExecutablePath(QStringLiteral(" C:/Games/Fallout4.exe "), {}),
             QStringLiteral("C:/Games/Fallout4.exe"));
}

QTEST_MAIN(GamePathUtilsTests)
#include "test_gamepathutils.moc"
