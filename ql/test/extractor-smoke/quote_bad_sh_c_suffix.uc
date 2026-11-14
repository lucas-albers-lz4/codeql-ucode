'use strict';
import { popen } from 'fs';
const methods = { probe: { call: function(request) {
	popen(`sh -c ${shellquote(request.args.value)} ignored`);
} } };
return methods;
