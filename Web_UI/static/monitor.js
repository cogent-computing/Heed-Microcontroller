const DUMMY_METRICS = {
    'battery state of charge (percentage)': [35, '%'],
    'power consumption (kw)': [1.25, 'kW'],
    'solar pv power generation (kw)': [1.25, 'kW'],
    'energy consumption 30days (kwh)': [56, 'kWh']
};

const DUMMY_PRIORITIES = {
    "0": ['Nursery 1', 'sockets'],
    "1": ['Playground', 'lights'],
    "2": ['Nursery 2', 'lights'],
    "3": ['Nursery 2', 'sockets'],
    "4": ['Nursery 1', 'lights'],
    "5": ['Playground', 'sockets']
};

/** stroke-7 font entities. */
const DEVTYPE_SYMBOLS = {
    'sockets': '&#xe69a',
    'lights': '&#xe643'
};

// For symbol e.g. <div class="mpick raised button">&#xe636;</div>
// though the .. looks cleaner I think
const METRIC_DIV = `
<div class="metric-detail" data-id="">
  <div class="mpick raised button">&#xe636;</div>
  <div class="metric-value text">
      <span class="metric meter"></span>
      <span class="mdesc"></span>
  </div>
  <div class="info highlight button">&#xe647;</div>
</div>
`

const PRIO_DIV = `
<div class="priority" data-id="">
  <div class="rank"></div>
  <div class="priority-detail text raised">
    <div class="load-type"></div>
    <div class="load-name"></div>
  </div>
</div>
`

/** i.e. if priority keys are 0..N-1, add 1. */
const PRIORITY_OFFSET = 1;

// #battery
const BATTERY_IND_SEL = "#battery-inner";

var _metrics = {};
var _priorities = null;
var _$currentMetric;
var _showLangs = false;
var _api_index = 0;
var _last_read = 0;
var _pending = {};

$(document).ready(function() {
    $('body').click(onMetricSelect);
    
    $('#expand').click(function() {
        if (document.fullscreenElement)
            document.exitFullscreen();
        else
            document.documentElement.requestFullscreen();
    });
    $('#priorities').sortable({containment: '#priorities', tolerance: 'pointer', axis: 'y',
        update: function() {
            var i = PRIORITY_OFFSET;
            var $prios = $('#priorities').children();
            $prios.each(function() {
                setPriority($(this), i++, $prios.length+1);
            });
            savePriorities();
        }
    });
    $('#refresh').click(function() { location.reload() });
    $('#help').click(function(e) {
        if ($('#help-display').css('display') == 'none')
        {
            e.stopPropagation();
            $('#metrics').css('display', 'none');
            $('#help-display').css('display', 'flex');
        }
    });
    
    $('#comms').attr('status', 'alert');

    checkBLS();
    initLang();
    addMetricsAndPriorities();
    hookData();
});

function addMetricsAndPriorities()
{
    for (var i = 0; i < NUM_METRICS; ++i)
        addMetric();
    
    seedMetrics();
    onMetrics({});
    
    if (TEST)
        onPriorities(DUMMY_PRIORITIES);
}

function onMetricSelect(e)
{
    $('#metrics').css('display', 'flex');
    $('#help-display').css('display', 'none');
    
    const id = $(e.target).data('id');
    if (id)
    {
        e.stopPropagation();
        setMetric(_$currentMetric, id);
        var m = [];
        $('.metric-detail').each(function() {
            m.push($(this).data('id'));
        });
        localStorage.setItem('metrics', JSON.stringify(m));
    }
    $('#select-metric').css('display', 'none');
    $('#info-metric').css('display', 'none');
    $('#metrics').css('display', 'flex');
}

function onMetrics(metrics)
{
    _metrics = metrics;
    onCharge(metrics[CHARGE_KEY]);
    onCharging(metrics[CHARGING_KEY]);
    
    $('.metric-value').each(function() {
        const id = $(this).parents('.metric-detail').data('id');
        setMetric($(this), id);
    });
    
    // Metric selector
    const metric_ids = Object.keys(_metrics);
    for (var i = 0; i < metric_ids.length; ++i)
    {
        // Would use ids here for direct lookup but can contain non-valid characters
        const metric_id = metric_ids[i];
        if (HIDE_METRICS.has(metric_id)) continue;
        
        if ($('[data-id="' + metric_id + '"]').length == 0)
        {
            var $nsm = $('<div data-id="' + metric_id + '">');
            setMetricName($nsm, metric_ids[i]);
            $nsm.addClass('smetric');
            $('#select-metric').append($nsm);
            
            var $hm = $('<div>');
            itext($hm, '_HELP_' + metric_id);
            $('#metric-help').append($hm);
        }
    }
}

function onCharge(charge)
{
    setMetricValue($('#charge'), charge, '%', true, true);
    if (charge)
    {
        cc = 'green';
        for (var i = 0; i < CHARGE_COLORS.length; ++i)
        {
            if (charge[0] < CHARGE_COLORS[i][0])
            {
                cc = CHARGE_COLORS[i][1];
                break;
            }
        }
        // Bit of a fudge on width, to account for being a bit smaller on battery width
        const inset = 'calc(var(--battery-width) * -' + Math.max(0.025, charge[0]/103) + ')';
        $(BATTERY_IND_SEL).css('box-shadow', 'inset ' + inset + ' 0 0 ' + cc);
    }
    else
        $(BATTERY_IND_SEL).css('background-color', 'unset').css('box-shadow', 'unset');
}

function onCharging(charging)
{
    const show = charging == null || charging[0];
    if (show)
        $('#charging').attr('status', charging == null ? 'none' : 'ok');
    $('#charging').toggleClass('stealth', !show);
}

function onPriorities(prios)
{
    var changed = true;
    if (_priorities != null && Object.keys(prios).length == Object.keys(_priorities).length)
    {
        changed = false
        const keys = Object.keys(prios);
        for (var i = 0; i < keys.length; ++i)
        {
            const a = _priorities[keys[i]];
            const b = prios[keys[i]];
            if (!a || a[0] != b[0] || a[1] != b[1])
            {
                changed = true;
                break;
            }
        }
    }
    _priorities = prios;

    if (changed)
    {
        $('#priorities').sortable('cancel');
        $('#priorities>.priority').data('rank', -1);
    }
    
    const pkeys = Object.keys(prios);
    for (var i = 0; i < pkeys.length; ++i)
    {
        const pkey = pkeys[i];
        const prio = prios[pkey];
        var $div = $('#priorities>.priority[data-id="' + prio[0] + '"]');
        if ($div.length == 0)
        {
            $div = $(PRIO_DIV);
            $div.attr('data-id', prio[0]);
            $('#priorities').append($div);
        }
        setPriority($div, i, pkeys.length);
        itext($div.find('.load-name'), prio[0]);
        $div.find('.load-type').html(DEVTYPE_SYMBOLS[prio[1]]);
    }
    if (changed)
    {
        $('#priorities>.priority').each(function() {
            if ($(this).data('rank') == '-1')
                $(this).remove();
        });
        
        $('#priorities>.priority').detach().sort(function(a, b) {
            return $(a).data('rank') > $(b).data('rank');
        }).appendTo('#priorities');
    }
}

function setPriority($div, priority, numPriorities)
{
    $div.data('rank', priority);
    if (SIMPLE_PRIORITIES)
        itext($div.find('.rank'), priority < (numPriorities/2) ? 'High' : 'Low');
    else
        $div.find('.rank').text((priority | 0) + PRIORITY_OFFSET);
}

function savePriorities()
{
    var d = {};
    $('#priorities>.priority').each(function() {
        d[$(this).data('rank')] = $(this).data('id');
    });
    _priorities = d;
    console.log('Setting priorities', d);
    $.ajax({
        url: API[_api_index] + '/update_priorities',
        method: 'POST',
        data: JSON.stringify({'priorities': d}),
        contentType: "application/json; charset=utf-8",
    });
}

function seedMetrics()
{
    // Load from BLS if present
    var mconf = JSON.parse(localStorage.getItem('metrics')) || DEFAULT_METRICS;
    var i = 0;
    $('.metric-detail').each(function() {
        if (!HIDE_METRICS.has(mconf[i]))
            setMetric($(this), mconf[i]);
        ++i;
    });
}

function setMetric($c, metric_id)
{
    setMetricValue($c.find('.metric'), _metrics[metric_id]);
    var $md = $c.find('.mdesc');
    setMetricName($md, metric_id);
    $c.data('id', metric_id);
}

function setMetricName($n, metric_id)
{
    itext($n, metric_id);
    if (APPEND_UNITS && _metrics[metric_id] && _metrics[metric_id][1])
    {
        $n.text($n.text() + ' (' + _metrics[metric_id][1] + ')');
    }
}

function setMetricValue($n, metric, unit, round, naEmpty)
{
    if (metric == undefined)
        if (naEmpty) $n.text(''); else itext($n, 'N/A');
    else
    {
        $n.removeAttr('data-i');
        var t = !round ? metric[0].toFixed(2) : ((metric[0]+0.5) | 0);
        if (unit)
            $n.text(t + unit);
        else
            $n.text(t);
    }
}

function addMetric()
{
    var $m = $(METRIC_DIV);
    $m.find('.button').click(function(e) {
        e.stopPropagation();
        
        // Hide metrics panel
        $('#metrics').css('display', 'none');

        // Launch metric selector
        var $p = $(this).parents('.metric-detail');
        if ($(e.target).hasClass('mpick'))
        {
            var $m = $('#select-metric');
            $('#select-metric>.select').removeClass('select');        
            _$currentMetric = $p;
            $('#select-metric>[data-id="' + _$currentMetric.data('id') + '"]').addClass('select');
            $m.css('display', 'flex');
        }
        else
        {
            var $m = $('#info-metric');
            itext($m, '_HELP_' + $p.data('id'));
            $m.append($m);
            $m.css('display', 'flex');
        }
    });
    $('#metrics').append($m);
}

function checkBLS()
{
    // Clear BLS if version doesn't match
    if (localStorage.getItem('version') != VERSION)
    {
        localStorage.removeItem('lang');
        localStorage.removeItem('metrics');
        localStorage.setItem('version', VERSION);
    }
}

function initLang()
{
    const k = Object.keys(TRANS);
    for (var i = 0; i < k.length; ++i)
    {
        var $l = $('<div id="' + k[i] + '" class="lang">' + L('_lang', k[i]) + '</div>');
        $l.click(function() {
            if (_showLangs)
            {
                $('#'+LANG).removeClass('select');
                setLanguage($(this).attr('id'));
            }
            else
            {
                $('.lang').css('display', 'flex');
                $('#'+LANG).addClass('select');
            }
            _showLangs = !_showLangs;
        });
        if (k[i] != LANG) $l.css('display', 'none');
        $('#language').append($l);
    }
    setLanguage(localStorage.getItem('lang') || 'en');
}

function setLanguage(cc)
{
    localStorage.setItem('lang', cc);
    LANG = cc;
    $('.lang').css('display', 'none');
    $('#'+cc).css('display', 'flex');
    $('[data-i]').each(function() {
        $(this).text(L($(this).data('i')));
    });
}

function itext($n, val)
{
    // Need to update DOM for selector to work, data() doesn't
    $n.text(L(val)).attr('data-i', val);
}

function hookData()
{
    if (TEST)
    {
        setInterval(function() {
            mutate(_metrics);
            onMetrics(_metrics);
        }, 2000);
        onMetrics(DUMMY_METRICS);
    }
    else
    {
        pollAPI();
        setInterval(pollAPI, METRIC_POLL_RATE);
    }
}

function pollAPI()
{
    for (var i = 0; i <= _api_index; ++i)
    {
        // Prevent queueing queries if e.g. timeout exceeds poll rate
        if (!_pending[i])
        {
            _pending[i] = true;
            const url = API[i] + '/read_state/v2';        
            $.ajax({
                api_index: i,
                url: url,
                method: 'GET',
                timeout: API_TIMEOUT,
                dataType: 'json',
                success: function(data) {
                    if (this.api_index < _api_index) _api_index = this.api_index;
                    up();
                    
                    onPriorities(data.priorities);
                    var metrics = {};
                    for (var i = 0; i < data.system_state.length; ++i)
                    {
                        const d = data.system_state[i];
                        metrics[d[2]] = [d[0], d[1]];
                    }
                    onMetrics(metrics);
                },
                error: function(jqXHR, status, error) {
                    if (this.api_index == _api_index && _api_index < API.length-1) ++_api_index;
                    down();
                    console.log('Error reading state from API', API[i], status, error);
                },
                complete: function() { _pending[this.api_index] = false; }
            });
        }
    }
}

function up()
{
    _last_read = Date.now();
    $('#comms').attr('status', 'ok');
    $('#priorities').sortable('enable').css('overflow-y', 'scroll');
    $('#priority-lock').toggleClass('stealth', true);
}

function down()
{
    const downtime = Date.now() - _last_read;
    if (downtime > CLEAR_VALUES_TIMEOUT)
        onMetrics({});
    if (downtime > API_TIMEOUT + 1000)
    {
        $('#comms').attr('status', 'alert');        
        $('#priorities').sortable('disable');
        $('#priority-lock').toggleClass('stealth', false);
    }
}

function mutate(obj)
{
    const keys = Object.keys(obj);
    for (var i = 0; i < keys.length; ++i)
        obj[keys[i]][0] += obj[keys[i]][0]*(Math.random()-0.5)*0.1;
}