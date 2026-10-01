# Helsinki Region Bus Trips and Vehicle Successions, 2026-10-01

## Overview

This dataset contains 7,782 real bus trips of the Helsinki region transit network, recorded live on 2026-10-01 between 14:16 and 21:00 Helsinki time, together with the vehicle that ran each trip and the trip that the same vehicle ran next. It was recorded from the public high-frequency positioning feed of Digitransit and Helsinki Region Transport (HSL), which reports, for every vehicle in service, an event each time it arrives at, departs from or passes a stop.

The public timetable says which trips run but not which vehicle runs them. Which trip a vehicle works next is decided by each operator's internal duty schedule, which is not published. The HSL timetable publishes planned vehicle blocks for its trams but none for its buses, which is why this release contains buses only; the bus successions recorded here are not available from the timetable. We are not aware of any public archive of the positioning feed, and the records here were captured with the included recorder.

## Release At A Glance

- 7,782 bus trips run by 1,110 vehicles of 8 operators.
- 6,624 trips are followed by a recorded next trip of the same vehicle; the rest were the vehicle's last trip in the window.
- 1,520 stops with coordinates, every stop that begins or ends a listed trip.
- One service day, 2026-10-01, 14:16 to 21:00 Helsinki time.

## How The Data Was Collected

The feed was recorded with `collect.py`, included, which subscribes to the Digitransit MQTT broker `mqtt.hsl.fi` and keeps every arrival, departure, door and stop-passing event of every vehicle in service. Each event names the vehicle, the operator, the route, the direction and the scheduled start of the trip it is running, the stop, and the timetabled time at that stop.

`assemble.py`, included, turns the events into trips. A trip is one vehicle running one scheduled trip, keyed by operator, vehicle, route, direction and scheduled start. Its first and last stop and actual start and finish are the first and last recorded departure or arrival, and its scheduled finish is the timetabled time the feed reports at that last stop. Only bus trips are kept, and trips recorded at fewer than three stops are dropped. A trip's next trip is the following trip of the same vehicle, when it starts within three hours and no more than ten minutes before the earlier trip finished. Trip and vehicle identifiers are replaced by opaque keyed identifiers. Stop coordinates come from the HSL public timetable of the same day. Operator, route and stop identifiers are the feed's and the timetable's own, prefixed with `o`, `r` and `s`.

## Raw File Structure

The uploaded ZIP is flat and contains exactly these eight files at its root:

- `journeys.csv`: one row per trip: `journey_id`, `vehicle_id`, `operator`, `route`, `direction`, `scheduled_start`, `first_stop`, `last_stop`, `start_s`, `end_s`, `scheduled_end_s` (seconds after midnight Helsinki time), `n_stops`.
- `next_trips.csv`: one row per trip: `journey_id`, `next_journey_id`, the trip the same vehicle ran next, or `none`.
- `stops.csv`: `stop_id`, `name`, `lat`, `lon`.
- `collect.py`: the recorder.
- `assemble.py`: the program that turns the recorded events into the two tables, without the key used for the identifiers.
- `LICENSE`: CC BY 4.0 notice with the attribution required by Digitransit.
- `DATASET_DESCRIPTION.md`: this description, shipped inside the archive so the card and the data cannot drift apart.
- `PACKAGE_MANIFEST.sha256`: SHA-256 checksum of every other file in the package.

## Intended Use And Limitations

The dataset is intended for work on reconstructing vehicle duty chains from operating records, on assignment under the constraint that each trip is run by one vehicle, and on calibrated prediction over per-item candidate sets. It covers one afternoon and evening of one service day. Trips near the end of the window may lack their recorded next trip. Trips already under way when the recording began start at the first stop recorded after it began. The feed occasionally misses an event, so a few trips start or end at a stop after their true first or before their true last stop.

## Licence

CC BY 4.0. Contains data from Digitransit and Helsinki Region Transport (HSL), (c) Digitransit 2026, received 2026-10-01, licensed under CC BY 4.0. The records describe vehicles and timetabled trips and contain no personal data.
