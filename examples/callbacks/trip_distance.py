from eomaps import Maps

m = Maps()
m.add_feature.preset.ocean()
m.add_gridlines()

trip_points = []


def set_trip_points(event=None):
    if event is not None:
        trip_points.append(m.transform_plot_to_lonlat(event.xdata, event.ydata))

    if len(trip_points) > 1:
        with m.cb.click.make_artists_temporary():
            out_d_int, out_d_tot = m.add_line(
                trip_points, n=20, mark_points="r.", c="k", dynamic=True
            )

            m.add_text(
                0.01,
                -0.15,
                f"   Trip distance: {sum(out_d_tot)/1000:.2f} km",
                family="monospace",
                va="top",
            )


def clear_trip_points(event):
    if len(trip_points) > 0:
        m.cb.move._clear_temporary_artists()
        m._bm._clear_temp_artists("move")

        trip_points.pop(-1)

        set_trip_points()
        if event:
            draw_line(event)


def roundtrip(event):
    if (len(trip_points) > 1) and (trip_points[-1] != trip_points[0]):
        trip_points.append(trip_points[0])
        set_trip_points()

    # add roduntrip as permanent artist and clear trip-points (to re-start)
    out_d_int, out_d_tot = m.add_line(
        trip_points, n=20, mark_points="r.", c="k", dynamic=False
    )

    trip_points.clear()


def draw_line(event):
    if len(trip_points) > 0:
        with m.cb.move.make_artists_temporary():
            x, y = m.transform_plot_to_lonlat(event.xdata, event.ydata)
            out_d_int, out_d_tot = m.add_line(
                [trip_points[-1], [x, y]], n=20, c="k", lw=0.5, ls="--", dynamic=True
            )

            m.add_text(
                0.01,
                -0.05,
                f"Segment distance: {sum(out_d_tot)/1000:.2f} km",
                family="monospace",
                va="top",
            )
    else:
        with m.cb.move.make_artists_temporary():
            m.ax.plot(
                [event.xdata],
                [event.ydata],
                marker=r"$\bigoplus$",
                ms=15,
                markeredgecolor="none",
                markerfacecolor="k",
            )


m.cb.click.attach(set_trip_points, on_motion=True)
m.cb.click.attach(clear_trip_points, button=3, on_motion=True)
m.cb.click.attach(roundtrip, button=2)

m.cb.move.attach(draw_line)
m.cb.move.set_execute_during_toolbar_action(True)
