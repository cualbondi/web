// https://raw.githubusercontent.com/bbecquet/Leaflet.PolylineDecorator/master/leaflet.polylineDecorator.min.js
L.LineUtil.PolylineDecorator={computeAngle:function(a,b){return 180*Math.atan2(b.y-a.y,b.x-a.x)/Math.PI+90},getPointPathPixelLength:function(a){var b=a.length;if(2>b)return 0;for(var c=0,d=a[0],e=1;e<b;e++)c+=d.distanceTo(d=a[e]);return c},getPixelLength:function(a,b){var c=a instanceof L.Polyline?a.getLatLngs():a,d=c.length;if(2>d)return 0;for(var e=0,f=b.project(c[0]),g=1;g<d;g++)e+=f.distanceTo(f=b.project(c[g]));return e},projectPatternOnPath:function(a,b,c,d){var e=[],f;f=0;for(l=a.length;f<l;f++)e[f]=d.project(a[f]);a=this.projectPatternOnPointPath(e,b,c);f=0;for(l=a.length;f<l;f++)a[f].latLng=d.unproject(a[f].pt);return a},projectPatternOnPointPath:function(a,b,c){var d=[],e=this.getPointPathPixelLength(a)*c;b=this.interpolateOnPointPath(a,b);d.push(b);if(0<c){a=a.slice(b.predecessor);a[0]=b.pt;for(c=this.getPointPathPixelLength(a);e<=c;)b=this.interpolateOnPointPath(a,e/c),d.push(b),a=a.slice(b.predecessor),a[0]=b.pt,c=this.getPointPathPixelLength(a)}return d},interpolateOnPointPath:function(a,b){var c=a.length;if(2>c)return null;if(0>=b)return{pt:a[0],predecessor:0,heading:this.computeAngle(a[0],a[1])};if(1<=b)return{pt:a[c-1],predecessor:c-1,heading:this.computeAngle(a[c-2],a[c-1])};if(2==c)return{pt:this.interpolateBetweenPoints(a[0],a[1],b),predecessor:0,heading:this.computeAngle(a[0],a[1])};for(var d=this.getPointPathPixelLength(a),e=a[0],f=e,g=0,h=0,k=0,j=1;j<c&&h<b;j++)e=f,g=h,f=a[j],k+=e.distanceTo(f),h=k/d;return{pt:this.interpolateBetweenPoints(e,f,(b-g)/(h-g)),predecessor:j-2,heading:this.computeAngle(e,f)}},interpolateBetweenPoints:function(a,b,c){return b.x!=a.x?new L.Point(a.x*(1-c)+c*b.x,a.y*(1-c)+c*b.y):new L.Point(a.x,a.y+(b.y-a.y)*c)}};L.RotatedMarker=L.Marker.extend({options:{angle:0},_setPos:function(a){L.Marker.prototype._setPos.call(this,a);if(L.DomUtil.TRANSFORM)this._icon.style[L.DomUtil.TRANSFORM]+=" rotate("+this.options.angle+"deg)";else if(L.Browser.ie){var b=this.options.angle*L.LatLng.DEG_TO_RAD;a=Math.cos(b);b=Math.sin(b);this._icon.style.filter+=" progid:DXImageTransform.Microsoft.Matrix(sizingMethod='auto expand', M11="+a+", M12="+-b+", M21="+b+", M22="+a+")"}}});L.rotatedMarker=function(a,b){return new L.RotatedMarker(a,b)};L.Symbol=L.Symbol||{};L.Symbol.Dash=L.Class.extend({isZoomDependant:!0,options:{pixelSize:10,pathOptions:{}},initialize:function(a){L.Util.setOptions(this,a);this.options.pathOptions.clickable=!1},buildSymbol:function(a,b,c){b=this.options;if(1>=b.pixelSize)return new L.Polyline([a.latLng,a.latLng],b.pathOptions);var d=c.project(a.latLng);a=-(a.heading-90)*L.LatLng.DEG_TO_RAD;a=new L.Point(d.x+b.pixelSize*Math.cos(a+Math.PI)/2,d.y+b.pixelSize*Math.sin(a)/2);d=d.add(d.subtract(a));return new L.Polyline([c.unproject(a),c.unproject(d)],b.pathOptions)}});L.Symbol.dash=function(a){return new L.Symbol.Dash(a)};L.Symbol.ArrowHead=L.Class.extend({isZoomDependant:!0,options:{polygon:!0,pixelSize:10,headAngle:60,pathOptions:{stroke:!1,weight:2}},initialize:function(a){L.Util.setOptions(this,a);this.options.pathOptions.clickable=!1},buildSymbol:function(a,b,c){b=this.options;return b.polygon?new L.Polygon(this._buildArrowPath(a,c),b.pathOptions):new L.Polyline(this._buildArrowPath(a,c),b.pathOptions)},_buildArrowPath:function(a,b){var c=b.project(a.latLng),d=-(a.heading-90)*L.LatLng.DEG_TO_RAD,e=this.options.headAngle/2*L.LatLng.DEG_TO_RAD,f=d+e,d=d-e,f=new L.Point(c.x-this.options.pixelSize*Math.cos(f),c.y+this.options.pixelSize*Math.sin(f)),c=new L.Point(c.x-this.options.pixelSize*Math.cos(d),c.y+this.options.pixelSize*Math.sin(d));return[b.unproject(f),a.latLng,b.unproject(c)]}});L.Symbol.arrowHead=function(a){return new L.Symbol.ArrowHead(a)};L.Symbol.Marker=L.Class.extend({isZoomDependant:!1,options:{markerOptions:{},rotate:!1},initialize:function(a){L.Util.setOptions(this,a);this.options.markerOptions.clickable=!1;this.options.markerOptions.draggable=!1;this.isZoomDependant=L.Browser.ie&&this.options.rotate},buildSymbol:function(a){return this.options.rotate?(this.options.markerOptions.angle=a.heading,new L.RotatedMarker(a.latLng,this.options.markerOptions)):new L.Marker(a.latLng,this.options.markerOptions)}});L.Symbol.marker=function(a){return new L.Symbol.Marker(a)};L.PolylineDecorator=L.LayerGroup.extend({options:{patterns:[]},initialize:function(a,b){L.LayerGroup.prototype.initialize.call(this);L.Util.setOptions(this,b);this._map=null;this._initPaths(a);this._initPatterns()},_initPaths:function(a){this._paths=[];var b=!1;if(a instanceof L.MultiPolyline||(b=a instanceof L.MultiPolygon)){a=a.getLatLngs();for(var c=0;c<a.length;c++)this._initPath(a[c],b)}else if(a instanceof L.Polyline)this._initPath(a.getLatLngs(),a instanceof L.Polygon);else if(L.Util.isArray(a)&&0<a.length)if(a[0]instanceof L.Polyline)for(c=0;c<a.length;c++)this._initPath(a[c].getLatLngs(),a[c]instanceof L.Polygon);else this._initPath(a)},_isCoordArray:function(a){return L.Util.isArray(a)&&0<a.length&&(a[0]instanceof L.LatLng||L.Util.isArray(a[0])&&2==a[0].length&&"number"===typeof a[0][0])},_initPath:function(a,b){var c;c=this._isCoordArray(a)?[a]:a;for(var d=0;d<c.length;d++)b&&c[d].push(c[d][0]),this._paths.push(c[d])},_initPatterns:function(){this._isZoomDependant=!1;this._patterns=[];for(var a,b=0;b<this.options.patterns.length;b++)a=this._parsePatternDef(this.options.patterns[b]),this._patterns.push(a),this._isZoomDependant=this._isZoomDependant||a.isOffsetInPixels||a.isRepeatInPixels||a.symbolFactory.isZoomDependant},setPatterns:function(a){this.options.patterns=a;this._initPatterns();this._softRedraw()},setPaths:function(a){this._initPaths(a);this.redraw()},_parsePatternDef:function(a){var b={cache:[],symbolFactory:a.symbol,isOffsetInPixels:!1,isRepeatInPixels:!1};"string"===typeof a.offset&&-1!=a.offset.indexOf("%")?b.offset=parseFloat(a.offset)/100:(b.offset=parseFloat(a.offset),b.isOffsetInPixels=0<b.offset);"string"===typeof a.repeat&&-1!=a.repeat.indexOf("%")?b.repeat=parseFloat(a.repeat)/100:(b.repeat=parseFloat(a.repeat),b.isRepeatInPixels=0<b.repeat);return b},onAdd:function(a){this._map=a;this._draw();if(this._isZoomDependant)this._map.on("zoomend",this._softRedraw,this)},onRemove:function(a){this._map.off("zoomend",this._softRedraw,this);this._map=null;L.LayerGroup.prototype.onRemove.call(this,a)},_buildSymbols:function(a,b,c){for(var d=[],e=0,f=c.length;e<f;e++)d.push(b.buildSymbol(c[e],a,this._map,e,f));return d},_getCache:function(a,b,c){var d=a.cache[b];return"undefined"===typeof d?(a.cache[b]=[],null):d[c]},_getDirectionPoints:function(a,b){var c=this._map.getZoom(),d=this._getCache(b,c,a);if(d)return d;var e;e=null;var f=this._paths[a];b.isOffsetInPixels?(e=L.LineUtil.PolylineDecorator.getPixelLength(f,this._map),d=b.offset/e):d=b.offset;b.isRepeatInPixels?(e=null!==e?e:L.LineUtil.PolylineDecorator.getPixelLength(f,this._map),e=b.repeat/e):e=b.repeat;d=L.LineUtil.PolylineDecorator.projectPatternOnPath(f,d,e,this._map);return b.cache[c][a]=d},redraw:function(){this._redraw(!0)},_softRedraw:function(){this._redraw(!1)},_redraw:function(a){if(null!==this._map){this.clearLayers();if(a)for(a=0;a<this._patterns.length;a++)this._patterns[a].cache=[];this._draw()}},_drawPattern:function(a){for(var b,c=0;c<this._paths.length;c++){b=this._getDirectionPoints(c,a);b=this._buildSymbols(this._paths[c],a.symbolFactory,b);for(var d=0;d<b.length;d++)this.addLayer(b[d])}},_draw:function(){for(var a=0;a<this._patterns.length;a++)this._drawPattern(this._patterns[a])}});L.polylineDecorator=function(a,b){return new L.PolylineDecorator(a,b)};

            // http://makinacorpus.github.io/Leaflet.TextPath/leaflet.textpath.js
            // plugin leaflet para las flechitas en la polilinea.
            /*
             * Inspired by Tom Mac Wright article :
             * http://mapbox.com/osmdev/2012/11/20/getting-serious-about-svg/
             */

            (function () {

            var __onAdd = L.Polyline.prototype.onAdd,
                __onRemove = L.Polyline.prototype.onRemove,
                __updatePath = L.Polyline.prototype._updatePath,
                __bringToFront = L.Polyline.prototype.bringToFront;


            var PolylineTextPath = {

                onAdd: function (map) {
                    __onAdd.call(this, map);
                    this._textRedraw();
                },

                onRemove: function (map) {
                    map = map || this._map;
                    if (map && this._textNode)
                        map._pathRoot.removeChild(this._textNode);
                    __onRemove.call(this, map);
                },

                bringToFront: function () {
                    __bringToFront.call(this);
                    this._textRedraw();
                },

                _updatePath: function () {
                    __updatePath.call(this);
                    this._textRedraw();
                },

                _textRedraw: function () {
                    var text = this._text,
                        options = this._textOptions;
                    if (text) {
                        this.setText(null).setText(text, options);
                    }
                },

                setText: function (text, options) {
                    this._text = text;
                    this._textOptions = options;

                    var defaults = {repeat: false, fillColor: 'black', attributes: {}};
                    options = L.Util.extend(defaults, options);

                    /* If empty text, hide */
                    if (!text) {
                        if (this._textNode)
                            this._map._pathRoot.removeChild(this._textNode);
                        return this;
                    }

                    text = text.replace(/ /g, '\u00A0');  // Non breakable spaces
                    var id = 'pathdef-' + L.Util.stamp(this);
                    var svg = this._map._pathRoot;
                    this._path.setAttribute('id', id);

                    if (options.repeat) {
                        /* Compute single pattern length */
                        var pattern = L.Path.prototype._createElement('text');
                        for (var attr in options.attributes)
                            pattern.setAttribute(attr, options.attributes[attr]);
                        pattern.appendChild(document.createTextNode(text));
                        svg.appendChild(pattern);
                        var alength = pattern.getComputedTextLength();
                        svg.removeChild(pattern);

                        /* Create string as long as path */
                        text = new Array(Math.ceil(this._path.getTotalLength() / alength)).join(text);
                    }

                    /* Put it along the path using textPath */
                    var textNode = L.Path.prototype._createElement('text'),
                        textPath = L.Path.prototype._createElement('textPath');

                    var dy = options.offset || this._path.getAttribute('stroke-width');

                    textPath.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", '#'+id);
                    textNode.setAttribute('dy', dy);
                    for (var attr in options.attributes)
                        textNode.setAttribute(attr, options.attributes[attr]);
                    textPath.appendChild(document.createTextNode(text));
                    textNode.appendChild(textPath);
                    svg.appendChild(textNode);
                    this._textNode = textNode;
                    return this;
                }
            };

            L.Polyline.include(PolylineTextPath);

            L.LayerGroup.include({
                setText: function(text, options) {
                    for (var layer in this._layers) {
                        if (typeof this._layers[layer].setText === 'function') {
                            this._layers[layer].setText(text, options);
                        }
                    }
                    return this;
                }
            });

            })();
