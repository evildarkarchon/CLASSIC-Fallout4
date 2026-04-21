#include "signalhub.h"

SignalHub::SignalHub(QObject* parent)
    : QObject(parent)
{
}

SignalHub& SignalHub::instance()
{
    static SignalHub hub;
    return hub;
}
