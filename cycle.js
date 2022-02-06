function update_axis_event(e, axis) {
  if (axis=='x_axis') {
    x_axis = e.target.value;
    document.getElementById("x_axis_temp").value = x_axis;
  } else if (axis=='y1_axis') {
    y1_axis = e.target.value;
    document.getElementById("y1_axis_temp").value = y1_axis;
  } else if (axis=='graph_type') {
    graph_type = e.target.value;
    document.getElementById("graph_type_temp").value = graph_type;
  } else if (axis=='phase_fold') {
    phase_fold = e.target.value;
    document.getElementById("phase_fold_temp").value = phase_fold;
  } else {
    document.getElementById("errormsg").value = "Error: axis '"+ axis +"' is not yet coded";
  }
  if (x_axis=='Date' && graph_type == 'scatter' && searchtype != 'Years') { $('.option1').show(); }
  else { $('.option1').hide(); }
  // Press submitbutton as graph can't yet be redrawn
  document.getElementById("mysqlform").submit();        // !name can't be "submit", otherwise this command won't work ->  input type="submit" name="submitbutton" value="Search"/>
  //update_graph_data(x_axis, y1_axis, graph_type, phase_fold, graphTarget);
}

function assign_data_to_axis(axis, ii, graph_type) {
  if (axis=="Date"){
    if (graph_type=="scatter") {var temp=new Date(data[ii].Date);}
    else {var temp=data[ii].Date;}
  }
  else if (axis=="Distance"){var temp=data[ii].KM;}
  else if (axis=="Time"){var temp=data[ii].Seconds;}
  else if (axis=="Speed"){var temp=data[ii].KMH;}
  //document.write(temp);
  return temp;
}

function update_graph_data(x_axis, y1_axis, graph_type, phase_fold, graphTarget) { 
  var xx = [];
  var yy1 = [];
  var xy = [];
  var dividor = 0;
  var phase_fold_number = 0;
  const sec_per_day = 24*3600;
  const millisec_per_day = sec_per_day*1000;
  if (phase_fold=='Year') {phase_fold_number = 365.25}
  else if (phase_fold=='Month') {phase_fold_number = 30.4}
  else if (phase_fold=='Week') {phase_fold_number = 7}
  if (phase_fold_number > 0 && x_axis=='Date' && graph_type == 'scatter') {
    dividor=phase_fold_number*millisec_per_day;
    var xy = {};
  } else {
    var xy = [];
  }
  
  for (var ii in data) {
    x1 = assign_data_to_axis(x_axis,ii, graph_type);
    y1 = assign_data_to_axis(y1_axis,ii, graph_type);
    if (dividor > 0) {
      var phase = (x1-min_date)/dividor;        // cycle.phase
      //document.write(x1+' '+x1/1000+' '+phase);
      cycle = Math.floor(phase)
      x1 = new Date( (phase - cycle)*dividor+min_date );
      //document.write(' '+x1+' '+(phase - Math.floor(phase))*millisec_per_day+'\n');
      if (!xy[cycle]) {xy[cycle] = [];}
      xy[cycle].push({x:x1, y:y1});
    }
    else {
      xy.push({x:x1, y:y1});
    }
    xx.push(x1);
    yy1.push(y1);
    
  }
  showGraph(xx, yy1, xy, x_axis, y1_axis, graph_type, graphTarget, phase_fold, phase_fold_number); 
  
}

function showGraph(xx, yy1, xy, x_axis, y1_axis, graph_type, graphTarget, phase_fold, phase_fold_number){
  //graphTarget.remove();
  // doesn't work, can't create chart and Canvas is already in use // document.querySelector("#graphCanvas").remove(); $(document).ready(function(){$("#chart-container").append('<canvas id="graphCanvas"></canvas>');}); graphTarget = document.querySelector("#graphCanvas");
  //document.querySelector("#chart-container").append('<canvas id="graphCanvas"></canvas>');
  // doesn't work, is always undefined, probably as in fucntion // if (typeof barGraph != "undefined") {barGraph.destroy();}
  // doesn't work, is always undefined, probably as in fucntion // if (window.barGraph != undefined) window.barGraph.destroy();
  //document.getElementById("to_log").innerHTML = graph_type;
  
  var chartoption_x_ticks = {};
  var chartoption_y_ticks = {};
  if (graph_type=="scatter") {
    chartoption_x_ticks =  {
                    callback: function(value, index, ticks) {
                        //return new Date(value).toLocaleDateString(undefined, {day: "numeric", month: "numeric",year: "numeric"});
                        if (x_axis=="Date" && graph_type=="scatter") {return new Date(value).toISOString().substring(0, 10);}
                        //else if (x_axis=="Date") {return new Date(value).toISOString().substring(0, 10);} // doesn't work, needs to be in the chartdata
                        else {return value;}        // this whole section shouldn't be there for not scatter
                    }
                 }
    chartoption_y_ticks =  {
                    // min: Math.min(yy1),        // v2, but not necessary
                    // max: Math.max(yy1),        // v2, but not necessary
                    callback: function(value, index, ticks) {
                        //return new Date(value).toLocaleDateString(undefined, {day: "numeric", month: "numeric",year: "numeric"});
                        if (y1_axis=="Date") {return new Date(value).toISOString().substring(0, 10);}
                        else {return value;}
                    }
    }
  };
  
  var chartoption = {
             scales: {
               y: {
                 scaleLabel: {
                   display: true,           // Chart.js version 2
                   labelString: y1_axis     // Chart.js version 2
                 },
                 title: {
                   display: true,           // Chart.js version 3
                   text: y1_axis            // Chart.js version 3
                 },
                 ticks: chartoption_y_ticks,
                 // suggestedMin: Math.min(yy1),        // v3, but not necessary
                 // suggestedMax: Math.max(yy1),        // v3, but not necessary
               },
               x: {
                 scaleLabel: {
                   display: true,           // Chart.js version 2
                   labelString: x_axis     // Chart.js version 2
                 },
                 title: {
                   display: true,           // Chart.js version 3
                   text: x_axis            // Chart.js version 3
                 },
                 ticks: chartoption_x_ticks
               }
             },
             plugins: {
              zoom: {
                zoom: {
                  wheel: {
                    enabled: true,
                  },
                  drag: {
                    enabled: true,
                  },
                  pinch: {
                    enabled: true,
                  },
                  mode: 'xy',
                }
              },
              colorschemes: {
                scheme: 'brewer.Paired12' //'tableau.Tableau20'
              }
            }
            //scales: {xAxes: [{type: "datetime"}]}
            //scales: {xAxes: [{ticks: {callback: (value) => {return new Date(value).toLocaleDateString("fa-IR", {month: "short",year: "numeric"});}}}]}
  }

  if (graph_type=="scatter" && phase_fold_number == 0) {
    var chartdata = {
            datasets: [{
              label: y1_axis,     // this is for legend
              pointBackgroundColor: "rgba(0,0,255,1)",
              hoverBackgroundColor: '#CCCCCC',
              hoverBorderColor: '#666666',
              pointRadius: 2,
              data: xy
            }]
    };
  } else if (graph_type=="scatter") {
    var chartdata_entries = [];
    var first_entry_txt = y1_axis+'_';
    for (const key in xy) {
      //document.write(Object.keys(xy).length);
      chartdata_entries.push({
              label: first_entry_txt+phase_fold+key,     // this is for legend
              //pointBackgroundColor: "rgba(0,0,255,1)",
              //hoverBackgroundColor: '#CCCCCC',
              //hoverBorderColor: '#666666',
              pointRadius: 2,
              showLine: true,
              data: xy[key]
      });
      first_entry_txt = '';
    }
    var chartdata = {datasets: chartdata_entries};
  } else {
    var chartdata = {
                labels: xx,
                datasets: [{
                                label: y1_axis,
                                backgroundColor: '#49e2ff',
                                borderColor: '#46d5f1',
                                hoverBackgroundColor: '#CCCCCC',
                                hoverBorderColor: '#666666',
                                pointRadius: 2,
                                data: yy1
                }]
    };
  }

  var myGraph = new Chart(graphTarget, {
           type: graph_type,
           data: chartdata,
           options: chartoption,
  });
         
}
