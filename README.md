# ptrack
*Track all sorts of packages.*

You write all your tracking wishes into a file structured like this:

```
<tracking id> <postal service name> <name>
<tracking id> <postal service name> <name>
...
```

Where the postal service name can be gathered from the list further down this README. Quoting strings containing spaces is supported.

After that you can run `python3 -m ptrack.cli view /path/to/trackers_file` to see an automatically updating view of the trackers.


## Supported services:

 - DHL Germany (`dhl`)
 - Asendia (`asendia`)
 - GlobalPost (`globalpost`) (very basic implementation, missing accurate progress and other bits.)

### Planned
 
 - Hermes Germany (`hermes`)
 - UPS (`ups`)
 - DHL International (`dhl_int`)

## Modular structure

To add a postal service tracking service, implement the `ptrack.modules.models.TrackingSupplier` class.

You should bundle your settings into a dataclass object which is your "settings class". Your class must expose
the `get_details_for` method.
