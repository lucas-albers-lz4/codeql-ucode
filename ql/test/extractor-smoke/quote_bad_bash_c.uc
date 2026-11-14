'use strict';
import { popen } from 'fs';
const methods = { probe: { call: function(request) {
	popen(`bash -c ${shellquote(request.args.value)} ignored`);
} } };
return methods;
