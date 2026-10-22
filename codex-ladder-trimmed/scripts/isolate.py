"""Mount namespace hides benchmark tree; drop capabilities before agent execution."""
import os,sys
if __name__=='__main__':
 work=sys.argv[1]
 script='mount --make-rprivate / && mount -t tmpfs -o size=1m tmpfs /workspace/work && exec setpriv --bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs "$@"'
 os.execvp('unshare',['unshare','-Urmpf','--mount-proc','bash','-c',script,'isolated',*sys.argv[2:]])
