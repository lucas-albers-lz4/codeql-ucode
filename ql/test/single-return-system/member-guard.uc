const methods = {
  setBlockDetect: { call: function(request) {
    if (!session.access(request.sid, 'file', '/bin/true', 'exec')) return {};
    return { result: system('/bin/true') == 0 };
  } }
};
return { luci: methods };
