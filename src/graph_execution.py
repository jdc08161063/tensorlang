import graph_gen
import graph_io
import graph_query
import graph_xform

from tensorflow.python.framework import meta_graph

import tensorflow as tf
import sys

from tensorflow.python.client import timeline

def eprint(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)

def create_session():
  config = tf.ConfigProto(
    # log_device_placement=True,
    operation_timeout_in_ms=60000,
    inter_op_parallelism_threads=2,
  )

  return tf.Session(config=config)

def run_session(sess, result_pattern, feed_dict):
  tf.train.SummaryWriter('./logdir', sess.graph)
  eprint(tf.get_collection(tf.GraphKeys.QUEUE_RUNNERS))

  tf.global_variables_initializer()
  coord = tf.train.Coordinator()

  run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
  run_metadata = tf.RunMetadata()
  threads = tf.train.start_queue_runners(coord=coord)
  eprint("started %s" % threads)

  result_names, ops = graph_query.find_results(sess.graph, result_pattern)

  try:
    result_tensors = sess.run(
      fetches=ops,
      feed_dict=feed_dict,
      options=run_options,
      run_metadata=run_metadata,
    )

    return dict(zip(result_names, result_tensors))
  finally:
    # Create the Timeline object, and write it to a json
    tl = timeline.Timeline(run_metadata.step_stats)
    ctf = tl.generate_chrome_trace_format()
    with open('timeline.json', 'w') as f:
        f.write(ctf)

    coord.request_stop()
    coord.join(threads)

def import_and_run_meta_graph(meta_graph_def, result_pattern, feed_dict):
  with create_session() as sess:
    meta_graph.import_scoped_meta_graph(
      meta_graph_def,
      input_map=None,
    )

    return run_session(sess, result_pattern, feed_dict)


def run_imported_graph(graph_def, result_pattern, feed_dict):
  with create_session() as sess:
    tf.import_graph_def(
      graph_def,
      name=""
    )

    return run_session(sess, result_pattern, feed_dict)
