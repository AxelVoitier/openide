## Objectives

The objectives of this first refactoring are:

- [x] Internal reorganisation to clarify how things are structured
  - Splits up classes into various block/interfaces
  - If possible, makes typing more precise by narrowing it to one of those interface class instead of "the big class names"
- [x] Improve typing here and there
- [ ] Come-up with baseline tests
- [ ] Remove very useless fragments left-over from Netbeans
- [x] Bring in some docstrings to have a clearer idea of what methods are actually meant for

## Non-goals

- Do not transform the internal algorithm or change the internal structures
- Do not make the internal more Pythonic
- Do not over test the internal details
- Do not write proper end-user doc yet

## Optional goals

- [ ] NB bug fixes
- [ ] Transform some of the external API into something more usable/Pythonic
  - [ ] Iterator in the ChildFactory
  - [ ] Listeners
- [ ] Support asynchronous/lazy mode
- [ ] FilterNode
- [ ] Icons support
- [ ] Extensive actions support

## Done

### Documenting

- [x] Node
  - [x] GenericNode
  - [ ] FilterNode
- [x] Children
  - [x] ChildrenArray
  - [x] ChildrenMap
  - [x] ChildrenKeys
  - [x] SyncChildren
  - [ ] AsyncChildren
- [x] ChildFactory
- [x] EntrySupport
- [x] EntrySupportDefault
- [ ] EntrySupportLazy
- [x] ChildrenStorage
- [x] NodeListener & Co
- [ ] NodeLookup
- [ ] node_operations

### Restructuring and typing

- [x] Node
  - [x] GenericNode
  - [ ] FilterNode
- [x] Children
  - [x] ChildrenArray
  - [x] ChildrenMap
  - [x] ChildrenKeys
  - [x] SyncChildren
  - [ ] AsyncChildren
- [x] ChildFactory
- [x] EntrySupport
- [x] EntrySupportDefault
- [ ] EntrySupportLazy
- [x] ChildrenStorage
- [x] NodeListener & Co
- [x] NodeLookup
- [x] node_operations


### Tests

- [x] Node
  - [ ] GenericNode
  - [ ] FilterNode
- [x] Children
  - [x] ChildrenArray
  - [x] ChildrenMap
  - [x] ChildrenKeys
  - [x] SyncChildren
  - [ ] AsyncChildren
- [x] ChildFactory
- [x] EntrySupport
- [x] EntrySupportDefault
- [ ] EntrySupportLazy
- [x] ChildrenStorage
- [x] NodeListener & Co
- [ ] NodeLookup
- [x] node_operations


### Template

- [ ] Node
  - [ ] GenericNode
  - [ ] FilterNode
- [ ] Children
  - [ ] ChildrenArray
  - [ ] ChildrenMap
  - [ ] ChildrenKeys
  - [ ] SyncChildren
  - [ ] AsyncChildren
- [ ] ChildFactory
- [ ] EntrySupport
- [ ] EntrySupportDefault
- [ ] EntrySupportLazy
- [ ] ChildrenStorage
- [ ] NodeListener & Co
- [ ] NodeLookup
- [ ] node_operations
