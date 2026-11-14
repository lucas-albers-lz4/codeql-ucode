# Syntactic ubus.call inventory

`UbusCall` in `codeql.ucode.Concepts` recognizes a call whose direct callee is
the member expression `ubus.call`, using the typed call function, member object
and property fields. `UbusCallInventory.ql` identifies each such site as an
`ubus_call` syntactic fact at its source location. It does not resolve the
receiver's binding, determine the invoked implementation, analyze arguments or
reachability, or establish that a call succeeds. A different object bound to a
local variable named `ubus` can match. Computed properties, aliases,
parenthesized callees, and optional calls are not modeled.

The pinned LuCI plugin copy (`ql/test/extractor-smoke/SOURCE.txt`) has two
matches at lines 663 and 671 in `getOdhcp6cStats.call`. The focused smoke test
checks those locations and a synthetic direct call, while rejecting a bare
`call`, a different receiver, another `ubus` method, computed access, a
parenthesized callee, and optional member and call expressions. It does not emit `path_found`, assess authorization, or
attach OpenWrt UCI consumer records. `cursor().set` / `commit` are not modeled
by this slice.
