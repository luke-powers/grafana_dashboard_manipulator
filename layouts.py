'''Layout OrderedDicts, more efficient to return a new instance than
to deepcopy the OrderedDict.

'''

from collections import OrderedDict


def graph_target_layout():
    return OrderedDict(
        (
            ("refId", ""),
            ("hide", False),
            ("target", "")
        )
    )


def main_layout():
    '''Returns OrderedDict layout of main grafana json layout.

    '''
    return OrderedDict(
        (
            ("editable", True),
            ("hideControls", False),
            ("id", None),
            ("originalTitle", ""),
            ("refresh", "1m"),
            ("schemaVersion", 6),
            ("sharedCrosshair", False),
            ("style", "dark"),
            ("tags", []),
            ("timezone", "utc"),
            ("title", ""),
            ("version", 0),
            ("annotations",
             OrderedDict((("list",  []), ))
             ),
            ("nav", [
                OrderedDict((("type", "timepicker"),
                             ("collapse", False),
                             ("notice", False),
                             ("enable", True),
                             ("status", "Stable"),
                             ("now", True),
                             ("refresh_intervals", [
                                 "5s",
                                 "10s",
                                 "30s",
                                 "1m",
                                 "5m",
                                 "15m",
                                 "30m",
                                 "1h",
                                 "2h",
                                 "1d"
                             ]))
                            )
            ]
            ),
            ("rows", []),
            ("time", OrderedDict((("from", "now-6h"),
                                  ("to", "now")))
             )
        )
    )


# Possible to have multiple panels
def panel_layout():
    return OrderedDict(
        (
            ("aliasColors", {}),
            ("bars", False),
            ("datasource", ""),
            ("editable", True),
            ("error", False),
            ("fill", 4),
            ("height", "300"),
            ("id", None),
            ("leftyaxislabel", ""),
            ("lines", True),
            ("linewidth", 2),
            ("links", []),
            ("percentage", False),
            ("pointradius", 5),
            ("points", False),
            ("renderer", "png"),
            ("seriesOverrides", []),
            ("span", 6),
            ("stack", False),
            ("timeShift", None),
            ("title", ""),
            ("transparent", False),
            ("type", "graph"),
            ("x-axis", True),
            ("y-axis", True),
            ("grid", OrderedDict((("leftLogBase", 1),
                                  ("leftMax", None),
                                  ("leftMin", None),
                                  ("rightLogBase", 1),
                                  ("rightMax", None),
                                  ("rightMin", None),
                                  ("threshold1", None),
                                  ("threshold1Color", "rgba(215, 200, 25, 0.25)"),
                                  ("threshold2", None),
                                  ("threshold2Color", "rgba(235, 110, 110, 0.25)"),
                                  ("thresholdline", False)))
             ),
            ("legend", OrderedDict((
                ("alignastable", False),
                ("avg", False),
                ("current", False),
                ("hideempty", False),
                ("max", False),
                ("min", False),
                ("rightside", False),
                ("show", True),
                ("total", False),
                ("values", True)))
             ),
            ("targets", []),
            ("tooltip", OrderedDict((
                ("shared", True),
                ("value_type", "cumulative")))
             ),
            ("y_formats", [
                "short",
                "short"
            ]
            )
        )
    )


# Possible to have multiple rows
def row_layout():
    return OrderedDict(
        (
            ("collapse", False),
            ("editable", True),
            ("height", "250px"),
            ("panels", []),
            ("title", "")
        )
    )


# Templating for using Grafana templates
def template_layout():
    return OrderedDict(
        (
            ("list",
             [OrderedDict((("allFormat", "glob"),
                           ("current", OrderedDict((("tags", []),
                                                    ("text", "ca"),
                                                    ("value", "ca")))),
                           ("datasource", "Global"),
                           ("includeAll", False),
                           ("multi", False),
                           ("multiFormat", "glob"),
                           ("name", "colo"),
                           ("options", [OrderedDict((("selected", False),
                                                     ("text", "ca"),
                                                     ("value", "ca"))),
                                        OrderedDict((("selected", False),
                                                     ("text", "lc"),
                                                     ("value", "lc"))),
                                        OrderedDict((("selected", False),
                                                     ("text", "xa"),
                                                     ("value", "xa"))),
                                        OrderedDict((("selected", False),
                                                     ("text", "xf"),
                                                     ("value", "xf"))),
                                        OrderedDict((("selected", False),
                                                     ("text", "xv"),
                                                     ("value", "xv")))]),
                           ("query", ""),
                           ("refresh_on_load", True),
                           ("regex", ""),
                           ("type", "query")))
              ]),
        )
    )
