CHANGELOG
=========

0.0.1 - 30 June 2021
--------------------

- Initial dump of code
- Working Netbeans Selection Tutorial part 1
- A setuptools egg-info hook to generate openide.yaml file from
decorated classes in our and clients modules
- An egg-info lookup instance loader
- A global context (ie. focus aware) lookup
- The main lookup of the application (loaded by Lookup.get_default())
- Some ability to decorate a class as a service, with singleton
auto-loading from default/main lookup
- Basic setup of an application, with a very basic life-cycle
- Minimal implementation of TopComponent:
  - registration
  - open action
  - component lookup
  - activation
  - show/hide events
  - preferred ID
  - icon
  - and few other properties
- A context (ie. focus) tracker, in charge of updating the global
context lookup
- A main window implementation, connecting all those parts to form an
application following which top components are declared in the local
installation. Does handle:
  - locations of top components in the main
window
  - basic docking
  - loads up declared actions in menus
  - loads up top
components declared as open at startup
  - track focus and update the
context tracker
  - handle opening, closing and activation of top
components
