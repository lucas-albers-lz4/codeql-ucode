'use strict';

import { popen } from 'fs';

function run_command(section) {
	return popen(`lldpcli -f json0 show ${section}`, 'r');
}

const methods = {
	getStatus: {
		call: function(request) {
			return run_command(request.args.section);
		}
	}
};

if (true) {
	return { 'luci.synthetic': methods };
}
