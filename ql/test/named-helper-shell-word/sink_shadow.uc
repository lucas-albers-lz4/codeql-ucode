'use strict';

import { popen } from 'fs';

function run_command(section) {
	const popen = function(x) { return x; };
	return popen(`lldpcli -f json0 show ${section}`, 'r');
}

const methods = {
	getStatus: {
		call: function(request) {
			return run_command(request.args.section);
		}
	}
};

return { 'luci.synthetic': methods };
