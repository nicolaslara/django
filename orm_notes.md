# Making the ORM async

## Status

## Short term ToDo
 * Allow DatabaseWrapper to have both `.sync_connection` 
   and `.async_connection` and turn `.connection` into a property  
 * Make `ensure_connection()` work so that we don't require a call to `connect()` 
 * Move wrapping that passes self.a as self to the helper

## Open issues

 * Async backends only support autocommit
 * Keeping async and sync connections at the same time
 * Async backends rely on pools. We need to generalize the wrapper 
   to support pools 
 
## Required work
 
 * DefaultConnectionProxy needs to play well with the async abstractions
 * Modify `@async_unsafe` so that it is still used when calling that function 
   from a sync context, but ignored when called from an async context
 * Find a way to fail gracefully for unsupported features (like autocommit)
 * Deciding on an API / experimenting with different high level APIs
 * Implement other backends
 * Review potential issues with encodings and timezones in async mode in 
    - DatabaseWrapper.create_cursor (https://github.com/aio-libs/aiopg/blob/master/aiopg/cursor.py#L326)
    - DatabaseWrapper.init_connection_state
 
