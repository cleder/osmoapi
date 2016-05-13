# -*- coding: utf-8 -*-

import xml.etree.ElementTree as etree

import pygeoif
from requests_oauthlib import OAuth1Session

TEST_API_URL = 'http://api06.dev.openstreetmap.org/'
LIVE_API_URL = 'http://api.openstreetmap.org/'


class _OsmBaseObject(object):

    """
    Abstract Base Object with common Functionality.
    """

    def append_tags(self, element, **kwargs):
        """Append tags to a XML element."""
        for k, v in kwargs.items():
            tag_element = etree.SubElement(element, 'tag')
            tag_element.set('k', k)
            tag_element.set('v', v)

    def to_string(self):
        """Serialize XML etree element to String."""
        return etree.tostring(
            self.etree_element(),
            encoding='utf-8').decode('UTF-8')


class OsmChange(_OsmBaseObject):

    """
    **OsmChange.**

    http://wiki.openstreetmap.org/wiki/OsmChange

    osmChange is the file format used by osmosis (and osmconvert) to describe
    differences between two dumps of OSM data. However, it can also be used as
    the basis for anything that needs to represent changes. For example, bulk
    uploads/deletes/changes are also changesets and they can also be described
    using this format.

    """

    def __init__(self, changeset):
        self.nodes = []
        self.ways = []
        self.multipolygons = []
        self.idx = 0
        self.changeset = changeset

    def create_node(self, point, **kwargs):
        """
        **Create a Node.**

        http://wiki.openstreetmap.org/wiki/Node

        A node is one of the core elements in the OpenStreetMap data model.
        It consists of a single point in space defined by its latitude,
        longitude and node id.

        Nodes can be used to define standalone point features, but are more
        often used to define the shape or "path" of a way.
        """
        self.idx -= 1
        if not isinstance(point, dict):
            point = point.__geo_interface__
        assert point['type'] == 'Point'
        assert point['coordinates']
        lon = str(point['coordinates'][0])
        lat = str(point['coordinates'][1])
        self.nodes.append(dict(id=str(self.idx), lon=lon, lat=lat,
                               tags=dict(**kwargs)))
        return self.idx

    def create_way(self, linestring, **kwargs):
        """
        **Create a Way.**

        http://wiki.openstreetmap.org/wiki/Way

        A way is an ordered list of nodes which normally also has at least one
        tag or is included within a Relation.
        A way can have between 2 and 2,000 nodes. A way can be open or closed.
        A closed way is one whose last node on the way is also the first on that
        way. A closed way may be interpreted either as a closed polyline,
        or an area, or both.
        """
        if not isinstance(linestring, dict):
            linestring = linestring.__geo_interface__
        assert linestring['type'] == 'LineString' or linestring['type'] == 'LinearRing'
        assert linestring['coordinates']
        nodes = []
        for point in (pygeoif.Point(coord)
                      for coord in linestring['coordinates']):
            node = self.create_node(point)
            nodes.append(node)
        self.idx -= 1
        self.ways.append(dict(id=str(self.idx),
                              nodes=nodes,
                              tags=dict(**kwargs)))
        return self.idx

    def create_multipolygon(self, multipolygon, **kwargs):
        """
        **Create a Relation:multipolygon.**

        http://wiki.openstreetmap.org/wiki/Relation:multipolygon

        Any area that is complex (e.g., because its outline consists of several
        ways joined together, or because the area consists of multiple disjunct
        parts, or has holes) requires a multipolygon relation.

        A multipolygon relation can have any number of ways in the role outer
        (the outline) and any number of ways in the role inner (the holes),
        and these must form valid rings to build a multipolygon from.
        """
        if not isinstance(multipolygon, dict):
            multipolygon = multipolygon.__geo_interface__
        assert multipolygon['type'] == 'MultiPolygon' or multipolygon['type'] == 'Polygon'
        assert multipolygon['coordinates']
        if multipolygon['type'] == 'Polygon':
            polygons = [pygeoif.Polygon(pygeoif.as_shape(multipolygon)), ]
        else:
            polygons = []
            for coords in multipolygon['coordinates']:
                polygons.append(pygeoif.Polygon(coords[0], coords[1:]))
        ways = []
        for polygon in polygons:
            outer = self.create_way(polygon.exterior)
            ways.append(('outer', str(outer)))
            for way in polygon.interiors:
                inner = self.create_way(way)
                ways.append(('inner', str(inner)))
        self.idx -= 1
        self.multipolygons.append(dict(id=str(self.idx),
                                       ways=ways,
                                       tags=dict(**kwargs)))
        return self.idx

    def etree_element(self):
        """Create a XML representation of this change."""
        root = etree.Element('osmChange')
        create_element = etree.SubElement(root, 'create')
        for node in self.nodes:
            node_element = etree.SubElement(create_element, 'node')
            node_element.set('id', node['id'])
            node_element.set('lat', node['lat'])
            node_element.set('lon', node['lon'])
            node_element.set('changeset', str(self.changeset.id))
            self.append_tags(node_element, **node['tags'])
        for way in self.ways:
            way_element = etree.SubElement(create_element, 'way')
            way_element.set('id', way['id'])
            way_element.set('changeset', str(self.changeset.id))
            for node in way['nodes']:
                node_element = etree.SubElement(way_element, 'nd')
                node_element.set('ref', str(node))
            self.append_tags(way_element, **way['tags'])
        for mp in self.multipolygons:
            rel_element = etree.SubElement(create_element, 'relation')
            rel_element.set('id', mp['id'])
            rel_element.set('changeset', str(self.changeset.id))
            rel_element.set('id', mp['id'])
            for way in mp['ways']:
                member_element = etree.SubElement(rel_element, 'member')
                member_element.set('type', 'way')
                member_element.set('role', way[0])
                member_element.set('ref', way[1])
            self.append_tags(rel_element, **{'type': 'multipolygon'})
            self.append_tags(rel_element, **mp['tags'])
        return root


class ChangeSet(_OsmBaseObject):

    """
    **Changesets.**

    http://wiki.openstreetmap.org/wiki/API_v0.6#Changesets_2

    To make it easier to identify related changes the concept of changesets
    is introduced. Every modification of the standard OSM elements has to
    reference an open changeset. A changeset may contain tags just like the
    other elements. A recommended tag for changesets is the key `comment=*`
    with a short human readable description of the changes being made in that
    changeset, similar to a commit message in a revision control system. A new
    changeset can be opened at any time and a changeset may referenced from
    multiple API calls. Because of this it can be closed manually as the server
    can't know when one changeset ends and another should begin.
    """

    def __init__(self, id=None,
                 created_by='osmoapi v 0.1', comment='Changes via API',
                 **kwargs):
        """Initialize a changeset."""
        self.id = id
        self.created_by = created_by
        self.comment = comment
        self.kwargs = kwargs

    def etree_element(self):
        """Create a XML representation of this changeset."""
        root = etree.Element('osm')
        changeset = etree.SubElement(root, 'changeset')
        self.append_tags(changeset, created_by=self.created_by,
                         comment=self.comment)
        self.append_tags(changeset, **self.kwargs)
        return root


class OSMOAuthAPI(object):

    """OSM API with OAuth."""

    def __init__(self, client_key, client_secret, resource_owner_key,
                 resource_owner_secret, test=True):
        """
        Initialize a OAuth Session on either te test or Live server.

        It takes the OAuth Keys for the Application and current user
        to authenticate to OpenStreetMap, and the test parameter
        to decide if to run on the test or live server
        """
        self.session = OAuth1Session(
            client_key,
            client_secret=client_secret,
            resource_owner_key=resource_owner_key,
            resource_owner_secret=resource_owner_secret)
        if test:
            self.url = TEST_API_URL
        else:
            self.url = LIVE_API_URL

    def create_changeset(self, created_by, comment, **kwargs):
        """
        **Create: PUT /api/0.6/changeset/create.**

        http://wiki.openstreetmap.org/wiki/API_v0.6#Create:_PUT_.2Fapi.2F0.6.2Fchangeset.2Fcreate

        The payload of a changeset creation request has to be one or more
        changeset elements optionally including an arbitrary number of tags.
        Any number of possibly editor-specific, tags are allowed.
        An editor might, for example, automatically include information about
        which background image was used, or even a bit of internal state
        information that will make it easier to revisit the changeset with
        the same editor later, etc.

        Clients should include a `created_by=*` tag.
        Clients are advised to make sure that a `comment=*` is present,
        which the user has entered. It is optional at the moment but this might
        change in later API versions. Clients should not automatically generate
        the comment tag, as this tag is for the end-user to describe their
        changes. Clients may add any other tags as they see fit.
        """
        url = '{0}api/0.6/changeset/create'.format(self.url)
        changeset = ChangeSet(created_by=created_by, comment=comment, **kwargs)
        response = self.session.put(url, data=changeset.to_string())
        if response.status_code == 200:
            changeset.id = int(response.text)
            return changeset
        else:
            response.raise_for_status()

    def close_changeset(self, changeset):
        """
        **Close: PUT /api/0.6/changeset/#id/close.**

        http://wiki.openstreetmap.org/wiki/API_v0.6#Close:_PUT_.2Fapi.2F0.6.2Fchangeset.2F.23id.2Fclose

        Closes a changeset. A changeset may already have been closed without
        the owner issuing this API call. In this case an error code is returned.

        *Parameters:*

        **id**

        The id of the changeset to close. The user issuing this API call has to
        be the same that created the changeset.

        **Response**

        Nothing is returned upon successful closing of a changeset
        (HTTP status code 200).
        """
        url = '{0}api/0.6/changeset/{1}/close'.format(self.url, changeset.id)
        response = self.session.put(url)
        if response.status_code == 200:
            return True
        else:
            response.raise_for_status()

    def diff_upload(self, change):
        """
        **Diff upload: POST /api/0.6/changeset/#id/upload.**

        http://wiki.openstreetmap.org/wiki/API_v0.6#Diff_upload:_POST_.2Fapi.2F0.6.2Fchangeset.2F.23id.2Fupload

        With this API call files in the OsmChange format can be uploaded to the
        server. This is guaranteed to be running in a transaction. So either all
        the changes are applied or none.

        To upload an OSC file it has to conform to the OsmChange specification
        with the following differences:

        Each element must carry a changeset and a version attribute, except when
        you are creating an element where the version is not required as the
        server sets that for you. The changeset must be the same as the changeset
        ID being uploaded to.
        A `<delete>` block in the OsmChange document may have an `if-unused`
        attribute (the value of which is ignored). If this attribute is present,
        then the delete operation(s) in this block are conditional and will only
        be executed if the object to be deleted is not used by another object.
        Without the if-unused, such a situation would lead to an error, and the
        whole diff upload would fail.
        OsmChange documents generally have user and uid attributes on each
        element. These are not required in the document uploaded to the API.

        *Parameters:*


        **id**

        The ID of the changeset this diff belongs to.

        **POST data**

        The OsmChange file data.
        """
        url = '{0}api/0.6/changeset/{1}/upload'.format(self.url,
                                                       change.changeset.id)
        response = self.session.post(url, data=change.to_string())
        if response.status_code == 200:
            return response.text
        else:
            response.raise_for_status()
