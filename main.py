""" This Project aims at generating an action classifier from video streams
    I chose to develop my model based on the C3D structure
    It follows PEP8 coding conventions
    TensorFlow version: 1.10.0 """
import tensorflow as tf
import numpy as np
import time
import matplotlib.pyplot as plt
import random
import pickle


def load_and_preprocess_data():
    # load the data set into memory
    data_file1 = open("./youtube_action_train_data/youtube_action_train_data_part1.pkl", "rb")
    data_file2 = open("./youtube_action_train_data/youtube_action_train_data_part2.pkl", "rb")
    train_data1, train_labels1 = pickle.load(data_file1)
    train_data2, train_labels2 = pickle.load(data_file2)
    data_file1.close()
    data_file2.close()

    # combine the data
    loaded_data = np.float32(np.concatenate((train_data1, train_data2), axis=0))
    loaded_labels = np.concatenate((train_labels1, train_labels2), axis=0)

    num_data = len(loaded_data)
    num_labels = len(loaded_labels)

    loaded_data -= np.mean(loaded_data, axis=(2, 3, 4), keepdims=True)

    one_hot_labels = np.zeros((loaded_labels.size, loaded_labels.max() + 1), dtype=np.int64)
    one_hot_labels[np.arange(loaded_labels.size), loaded_labels] = 1
    loaded_labels = one_hot_labels
    print("data loaded")

    assert num_data == num_labels
    p = np.random.permutation(num_data)
    loaded_data, loaded_labels = loaded_data[p], loaded_labels[p]

    # choose the last 160 sequences to be the validation set
    num_validation = 160
    test_dataset, test_labelset, train_dataset, train_labelset = \
        loaded_data[num_data-num_validation:num_data], loaded_labels[num_data-num_validation:num_data], \
        loaded_data[:num_data-num_validation], loaded_labels[:num_data-num_validation]
    print("data shuffled!")

    return test_dataset/np.float32(255.0), test_labelset, train_dataset/np.float32(255.0), train_labelset


# CNN that was used for PA4
def conv_network(x_in):
    conv1_filter = tf.Variable(tf.truncated_normal(shape=[2, 2, 3, 64], mean=0, stddev=0.1))
    conv2_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 64, 128], mean=0, stddev=0.1))
    conv3_filter = tf.Variable(tf.truncated_normal(shape=[5, 5, 128, 256], mean=0, stddev=0.1))

    # credits to https://towardsdatascience.com/cifar-10-image-classification-in-tensorflow-5b501f7dc77c
    # I changed the model to 3 layers <- subject to changes
    conv1 = tf.nn.conv2d(x_in, conv1_filter, strides=[1, 1, 1, 1], padding='SAME')
    conv1 = tf.nn.relu(conv1)
    conv1_pool = tf.nn.max_pool(conv1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

    conv2 = tf.nn.conv2d(conv1_pool, conv2_filter, strides=[1, 1, 1, 1], padding='SAME')
    conv2 = tf.nn.relu(conv2)
    conv2_pool = tf.nn.max_pool(conv2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

    conv3 = tf.nn.conv2d(conv2_pool, conv3_filter, strides=[1, 1, 1, 1], padding='SAME')
    conv3 = tf.nn.softmax(conv3)
    conv3_pool = tf.nn.max_pool(conv3, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

    flat = tf.contrib.layers.flatten(conv3_pool)

    full1 = tf.contrib.layers.fully_connected(inputs=flat, num_outputs=256, activation_fn=tf.nn.relu)
    full1 = tf.layers.batch_normalization(full1)

    out = tf.contrib.layers.fully_connected(inputs=full1, num_outputs=500, activation_fn=tf.nn.relu)

    return out


# the same routine used for PA4 with LSTM
def lstm_output(x_data):
    rnn_input = tf.zeros([0, seq_length, 500])
    for i in range(batch_size):
        feed_in_cnn = tf.squeeze(tf.slice(x_data, [i, 0, 0, 0, 0], [1, seq_length, 64, 64, 3]), [0])
        # vectors generated by the CNN
        temp = conv_network(feed_in_cnn)  # (30, 500)
        rnn_input = tf.concat([rnn_input, tf.expand_dims(temp, 0)], 0)

    # the LSTM cell of the RNN
    lstm = tf.nn.rnn_cell.LSTMCell(num_units)
    h_val, _ = tf.nn.dynamic_rnn(lstm, rnn_input, dtype=tf.float32)

    # collection of all the final output
    temp_output = tf.zeros(shape=[batch_size, 0, 11])
    for i in range(seq_length):
        temp = tf.reshape(h_val[:, i, :], [batch_size, num_units])
        output = tf.matmul(temp, w_fc) + b_fc
        output = tf.reshape(output, [-1, 1, 11])
        temp_output = tf.concat([temp_output, output], axis=1)

    # 8x30x11
    flat = tf.reshape(temp_output, shape=[batch_size, 11*seq_length])
    final_output = tf.matmul(flat, w_out) + b_out

    return final_output


# I decided to use VGG CNN to train the model
def VGG_CNN(x_data):
    conv1_1_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 3, 64], mean=0, stddev=0.1))

    conv2_1_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 64, 128], mean=0, stddev=0.1))

    conv3_1_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 128, 256], mean=0, stddev=0.1))
    conv3_2_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 256, 256], mean=0, stddev=0.1))

    conv4_1_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 256, 512], mean=0, stddev=0.1))
    conv4_2_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 512, 512], mean=0, stddev=0.1))
    #
    # conv5_1_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 512, 512], mean=0, stddev=0.08))
    # conv5_2_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 512, 512], mean=0, stddev=0.08))

    # reference to https://neurohive.io/en/popular-networks/vgg16/
    conv1_1 = tf.nn.conv2d(x_data, conv1_1_filter, strides=[1, 1, 1, 1], padding='SAME')
    conv1_1 = tf.nn.relu(conv1_1)
    conv1_pool = tf.nn.max_pool(conv1_1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')
    conv1_bn = tf.layers.batch_normalization(conv1_pool)

    conv2_1 = tf.nn.conv2d(conv1_bn, conv2_1_filter, strides=[1, 1, 1, 1], padding='SAME')
    conv2_1 = tf.nn.relu(conv2_1)
    conv2_pool = tf.nn.max_pool(conv2_1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

    conv3_1 = tf.nn.conv2d(conv2_pool, conv3_1_filter, strides=[1, 1, 1, 1], padding='SAME')
    conv3_1 = tf.nn.relu(conv3_1)
    conv3_2 = tf.nn.conv2d(conv3_1, conv3_2_filter, strides=[1, 1, 1, 1], padding='SAME')
    conv3_2 = tf.nn.relu(conv3_2)
    conv3_pool = tf.nn.max_pool(conv3_2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

    conv4_1 = tf.nn.conv2d(conv3_pool, conv4_1_filter, strides=[1, 1, 1, 1], padding='SAME')
    conv4_1 = tf.nn.relu(conv4_1)
    conv4_2 = tf.nn.conv2d(conv4_1, conv4_2_filter, strides=[1, 1, 1, 1], padding='SAME')
    conv4_2 = tf.nn.relu(conv4_2)
    conv4_pool = tf.nn.max_pool(conv4_2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

    # conv5_1 = tf.nn.conv2d(conv4_pool, conv5_1_filter, strides=[1, 1, 1, 1], padding='SAME')
    # conv5_1 = tf.nn.relu(conv5_1)
    # conv5_2 = tf.nn.conv2d(conv5_1, conv5_2_filter, strides=[1, 1, 1, 1], padding='SAME')
    # conv5_2 = tf.nn.relu(conv5_2)
    # conv5_pool = tf.nn.max_pool(conv5_2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

    # flat = tf.contrib.layers.flatten(conv5_pool)
    flat = tf.contrib.layers.flatten(conv4_pool)
    flat_rl = tf.nn.relu(flat)

    full1 = tf.contrib.layers.fully_connected(inputs=flat_rl, num_outputs=2048, activation_fn=tf.nn.relu)
    full1_rl = tf.nn.relu(full1)

    full2 = tf.contrib.layers.fully_connected(inputs=full1_rl, num_outputs=2048, activation_fn=tf.nn.relu)
    full2_rl = tf.nn.relu(full2)

    out = tf.contrib.layers.fully_connected(inputs=full2_rl, num_outputs=500, activation_fn=tf.nn.softmax)

    return out


# 3D convolution NN
def c3d(x_data):
    # reference: https://www.kaggle.com/sentdex/first-pass-through-data-w-3d-convnet
    # and https: // arxiv.org / pdf / 1604.04494.pdf
    conv1_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 3, 3, 64], mean=0, stddev=0.1))

    conv2_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 3, 64, 128], mean=0, stddev=0.1))

    conv3_1_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 3, 128, 256], mean=0, stddev=0.1))
    conv3_2_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 3, 256, 256], mean=0, stddev=0.1))

    conv4_1_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 3, 256, 512], mean=0, stddev=0.1))
    conv4_2_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 3, 512, 512], mean=0, stddev=0.1))
    #
    # conv5_1_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 3, 256, 512], mean=0, stddev=0.1))
    # conv5_2_filter = tf.Variable(tf.truncated_normal(shape=[3, 3, 3, 512, 512], mean=0, stddev=0.1))

    conv1 = tf.nn.conv3d(x_data, conv1_filter, strides=[1, 1, 1, 1, 1], padding='SAME')
    conv1 = tf.nn.relu(conv1)
    conv1_pool = tf.layers.max_pooling3d(conv1, pool_size=[1, 2, 2], strides=[1, 2, 2], padding='SAME')

    conv2 = tf.nn.conv3d(conv1_pool, conv2_filter, strides=[1, 1, 1, 1, 1], padding='SAME')
    conv2 = tf.nn.relu(conv2)
    conv2_pool = tf.layers.max_pooling3d(conv2, pool_size=2, strides=2, padding='SAME')

    conv3_1 = tf.nn.conv3d(conv2_pool, conv3_1_filter, strides=[1, 1, 1, 1, 1], padding='SAME')
    conv3_1 = tf.nn.relu(conv3_1)
    conv3_2 = tf.nn.conv3d(conv3_1, conv3_2_filter, strides=[1, 1, 1, 1, 1], padding='SAME')
    conv3_2 = tf.nn.relu(conv3_2)
    conv3_pool = tf.layers.max_pooling3d(conv3_2, pool_size=2, strides=2, padding="SAME")

    conv4_1 = tf.nn.conv3d(conv3_pool, conv4_1_filter, strides=[1, 1, 1, 1, 1], padding='SAME')
    conv4_1 = tf.nn.relu(conv4_1)
    conv4_2 = tf.nn.conv3d(conv4_1, conv4_2_filter, strides=[1, 1, 1, 1, 1], padding='SAME')
    conv4_2 = tf.nn.relu(conv4_2)
    conv4_pool = tf.layers.max_pooling3d(conv4_2, pool_size=2, strides=2, padding="SAME")

    # conv5_1 = tf.nn.conv3d(conv4_pool, conv5_1_filter, strides=[1, 1, 1, 1, 1], padding='SAME')
    # conv5_1 = tf.nn.relu(conv5_1)
    # conv5_2 = tf.nn.conv3d(conv5_1, conv5_2_filter, strides=[1, 1, 1, 1, 1], padding='SAME')
    # conv5_2 = tf.nn.relu(conv5_2)
    # conv5_pool = tf.layers.max_pooling3d(conv5_2, pool_size=2, strides=2, padding="SAME")

    # flat = tf.contrib.layers.flatten(conv5_pool)
    flat = tf.contrib.layers.flatten(conv4_pool)
    # flat = tf.contrib.layers.flatten(conv3_pool)

    full1 = tf.contrib.layers.fully_connected(flat, num_outputs=1024, activation_fn=tf.nn.relu)
    full1 = tf.nn.dropout(full1, keep_prob=0.8)

    full2 = tf.contrib.layers.fully_connected(full1, num_outputs=1024, activation_fn=tf.nn.relu)
    full2 = tf.nn.dropout(full2, keep_prob=0.8)

    out = tf.contrib.layers.fully_connected(full2, num_outputs=11, activation_fn=tf.nn.softmax)

    return out


def vgg_post_process(x_data):
    out = tf.zeros([0, seq_length, 500])
    for iteration in range(batch_size):
        feed_in_cnn = tf.squeeze(tf.slice(x_data, [iteration, 0, 0, 0, 0], [1, seq_length, 64, 64, 3]), [0])
        # vectors generated by the CNN
        one_seq_convolved = VGG_CNN(feed_in_cnn)  # (30, 500)
        out = tf.concat([out, tf.expand_dims(one_seq_convolved, 0)], 0)

    # out = [8, 30, 500]
    flat = tf.contrib.layers.flatten(out)
    output = tf.contrib.layers.fully_connected(flat, num_outputs=11, activation_fn=tf.nn.softmax)
    return output


if __name__ == "__main__":
    # load the normalized data
    test_data, test_labels, train_data, train_labels = load_and_preprocess_data()

    # Remove previous weights, bias, inputs, etc.
    tf.reset_default_graph()

    # hyper-parameters
    batch_size = 16
    epoch_batch = 256
    num_epoch = 128
    learning_rate = 0.001
    num_units = 32
    seq_length = 30

    # filters
    w_fc = tf.Variable(tf.truncated_normal(shape=[num_units, 11], mean=0, stddev=0.1), name='w_fc')
    b_fc = tf.Variable(tf.zeros(shape=[11]), name='b_fc')

    w_out = tf.Variable(tf.truncated_normal(shape=[seq_length*11, 11], mean=0, stddev=0.1), name='w_fc')
    b_out = tf.Variable(tf.zeros(shape=[11]), name='b_fc')

    # each time the CNN takes in a set of 10 images and spit out 10 vectors
    x = tf.placeholder(dtype=tf.float32, shape=(batch_size, seq_length, 64, 64, 3), name='input_x')
    y = tf.placeholder(dtype=tf.int64, shape=(batch_size, 11), name='input_y')

    prediction = lstm_output(x)     # (8 ,11)

    print("Network in graph initialized!")

    # Loss and Optimizer
    prediction_op = tf.nn.softmax(prediction)

    loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits=prediction, labels=y))
    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(loss)

    # Save the model
    tf.get_collection('validation_nodes')
    # Add opts to the collection
    tf.add_to_collection('validation_nodes', x)
    tf.add_to_collection('validation_nodes', y)
    tf.add_to_collection('validation_nodes', prediction_op)

    # Accuracy
    y_pred = tf.argmax(prediction_op, 1)
    y_labels = tf.argmax(y, 1)

    correct_pred = tf.equal(y_pred, y_labels)

    # overall accuracy
    accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32), name='accuracy')

    saver = tf.train.Saver()

    # record_labels = []
    # record_predicts = []
    # accuracy_record = np.zeros([20, 1], dtype=np.float32)

    num_train = len(train_data)
    num_test = len(test_data)
    recognize = [[] for i in range(11)]

    accuracies = []
    with tf.Session() as sess:
        # Initializing the variables
        sess.run(tf.global_variables_initializer())

        # Training
        for epoch in range(num_epoch):
            # Loop over random batches
            for batch in range(epoch_batch):
                start_in_batch = random.randint(0, num_train - batch_size)
                x_batch, y_batch = train_data[start_in_batch: start_in_batch + batch_size], \
                    train_labels[start_in_batch: start_in_batch + batch_size]
                # record_labels.append(sess.run(y, feed_dict={x: x_batch, y: y_batch}))
                # record_predicts.append(sess.run(prediction, feed_dict={x: x_batch, y: y_batch}))
                sess.run(optimizer, feed_dict={x: x_batch, y: y_batch})

            print('Epoch {:>2}: '.format(epoch + 1), end='')

            loss_train = sess.run(loss, feed_dict={x: x_batch, y: y_batch})
            print("loss on train data: {:1.4f}".format(loss_train))

            # calculate test accuracy with 160 videos:
            temp_accu = np.zeros([160//batch_size, ])
            for test_batch in range(160//batch_size):
                x_valid, y_valid = test_data[test_batch*batch_size: (test_batch+1)*batch_size], \
                    test_labels[test_batch*batch_size: (test_batch+1)*batch_size]
                temp_accu[test_batch] = sess.run(accuracy, feed_dict={x: x_valid, y: y_valid})
            accuracies.append(np.mean(temp_accu))

            print("\taccuracy on test data: {}".format(accuracies[epoch]))
            if accuracies[epoch] >= 0.75:
                break

        for test_batch in range(160//batch_size):
            x_valid, y_valid = test_data[test_batch * batch_size: (test_batch + 1) * batch_size], \
                               test_labels[test_batch * batch_size: (test_batch + 1) * batch_size]

            get_predictions = sess.run(y_pred, feed_dict={x: x_valid, y: y_valid})
            get_labels = sess.run(y_labels, feed_dict={x: x_valid, y: y_valid})

            for i in range(len(get_labels)):
                recognize[get_labels[i]].append(get_predictions[i])

        save_path = saver.save(sess, "./my_model")
