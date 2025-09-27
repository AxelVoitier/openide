## Objectives

The objectives of this first refactoring are:

- [ ] Internal reorganisation to clarify how things are structured
  - Splits up classes into various block/interfaces
  - If possible, makes typing more precise by narrowing it to one of those interface class instead of "the big class names"
- [ ] Improve typing here and there
- [ ] Come-up with baseline tests
- [ ] Remove very useless fragments left-over from Netbeans
- [ ] Bring in some docstrings to have a clearer idea of what methods are actually meant for

## Non-goals

- Do not transform the internal algorithm or change the internal structures
- Do not make the internal more Pythonic
- Do not over test the internal details
- Do not write proper end-user doc yet

## Optional goals

- [ ] Transform some of the external API into something more usable/Pythonic
  - [ ] Iterator in the ChildFactory
  - [ ] Listeners
- [ ] Support asynchronous/lazy mode
- [ ] FilterNode

## Done

### Documenting

- [X] Node
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
- [X] ChildrenStorage
- [X] NodeListener & Co
- [ ] NodeLookup
- [ ] node_operations

### Restructuring and typing

- [ ] Node
  - [ ] GenericNode
  - [ ] FilterNode
- [x] Children
  - [x] ChildrenArray
  - [x] ChildrenMap
  - [x] ChildrenKeys
  - [ ] SyncChildren
  - [ ] AsyncChildren
- [x] ChildFactory
- [ ] EntrySupport
- [ ] EntrySupportDefault
- [ ] EntrySupportLazy
- [ ] ChildrenStorage
- [ ] NodeListener & Co
- [ ] NodeLookup
- [ ] node_operations


### Tests

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
