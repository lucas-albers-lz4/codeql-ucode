'use strict';
import { popen } from 'fs';
const methods = { probe: { call: function(request) {
	popen(`bash -ec ${shellquote(request.args.value)} ignored`);
} } };
return methods;
