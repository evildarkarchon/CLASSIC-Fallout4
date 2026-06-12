#include <QMetaObject>
#include <QSignalSpy>
#include <QtTest/QtTest>

#include "core/signalhub.h"

class SignalHubTests : public QObject {
    Q_OBJECT

private slots:
    void instance_returns_same_singleton_reference();
    void scanStarted_signal_is_emitted();
    void scanProgress_signal_carries_expected_payload();
};

void SignalHubTests::instance_returns_same_singleton_reference()
{
    SignalHub& first = SignalHub::instance();
    SignalHub& second = SignalHub::instance();
    QCOMPARE(&first, &second);
}

void SignalHubTests::scanStarted_signal_is_emitted()
{
    SignalHub& hub = SignalHub::instance();
    QSignalSpy spy(&hub, &SignalHub::scanStarted);

    const bool invoked = QMetaObject::invokeMethod(&hub, "scanStarted", Qt::DirectConnection);

    QVERIFY(invoked);
    QCOMPARE(spy.count(), 1);
}

void SignalHubTests::scanProgress_signal_carries_expected_payload()
{
    SignalHub& hub = SignalHub::instance();
    QSignalSpy spy(&hub, &SignalHub::scanProgress);

    const bool invoked = QMetaObject::invokeMethod(&hub, "scanProgress", Qt::DirectConnection, Q_ARG(float, 42.5F),
                                                   Q_ARG(QString, QStringLiteral("Scanning report...")));

    QVERIFY(invoked);
    QCOMPARE(spy.count(), 1);

    const auto args = spy.takeFirst();
    QCOMPARE(args.at(0).toFloat(), 42.5F);
    QCOMPARE(args.at(1).toString(), QStringLiteral("Scanning report..."));
}

QTEST_GUILESS_MAIN(SignalHubTests)
#include "test_signalhub.moc"
