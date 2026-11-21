# Direct formvalue syntax control

`dispatcher.uc` is the unchanged source from LuCI commit
`b2e0be4b46ec0fd43394c081fa7c50657af14011`, path
`modules/luci-base/ucode/dispatcher.uc`, Git blob
`99712b85e7bd1a22f300b00403bd66621b3d40f4`, SHA-256
`4f9923cf569aeebb956343d208bcc38f40d8a26d2f46f12c5539a9582fa4f037`.
See its upstream copyright and license header. The observer matches direct,
non-optional member syntax only. It does not resolve the `http` binding,
argument values or bindings, runtime behavior, taint, or authorization. It checks
the extracted first and second argument node classes, not their values. Aliased, computed and
optional calls are excluded. Matching an identifier named `http` does not prove
its binding is the HTTP API. This fixture does not establish dispatcher coverage.

The standalone smoke requires the built extractor pack; CI builds it in the
preceding M3 smoke. The pin and literal arguments are independently checked
against source text; they are not extracted argument-value assertions.
