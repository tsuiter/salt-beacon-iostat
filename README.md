=======================
Saltstack iostat beacon
=======================
This beacon reads information from /proc/diskstats file 

Documentation
=============

Installation:

 Add the iostat.py file to your root_dir/_beacons directory on your master server
 
 Sync the file to your minions
``` 
 salt '*' saltutil.sync_beacons
```
Beacon configuration:
 mininum configuration 
 ```
 iostat: {}
```  
Default values if not defined (matches all scsi disks, beacon if await > 20ms)

```
iostat:
  match_re: '^sd.*[a-z]$'
  output: min
  fields:
    await: 20
```

 All configuration options
 ```
iostat:
  match_re: '^sd.*[a-z]$'       #Regex string to match devices
  exclude_re: ''                #Regex string to exclude devices
  interval: 10                  #Interval in seconds to run beacon
  output: [full|min]            #If full return all values, not just threshold exceeded
  fields:                       #    https://www.kernel.org/doc/Documentation/iostats.txt
    await: <int value>          #read+write ms / read+write iops
    read_await: <int value>     #read ms / read iops  
    write_await: <int value>    #write ms / write iops
    stime: <int value>          #io ticks / read + read_merge + write + write_merge iops
    read: <int value>           #read iops 
    read_merge: <int value>     #read merges
    read_sectors: <int value>   #read sectors
    read_ms: <int value>        #read ms
    write: <int value>          #write iops
    write_merge: <int value>    #write merges
    write_sectors: <int value>  #write sectors
    write_ms: <int value>       #write ms
    org_active_io: <int value>  #Previous active IO
    new_active_io: <int value>  #current active IO
    io_ticks: <int value>       #time spend doing IO
    queue_ms: <int value>       #time waiting to do IO
 ```
