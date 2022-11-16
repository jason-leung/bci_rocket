from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import *
from PyQt5.QtGui import QPainter, QOpenGLTexture, QImage, QColor, QFont
from OpenGL.GL import *
from OpenGL.GLU import *
import os, copy, math, random
from pylsl import StreamInfo, StreamOutlet, StreamInlet, ContinuousResolver
import numpy as np

class OGLWidget(QOpenGLWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_AlwaysStackOnTop)
        self.colors = [QColor(255,0,0), QColor(0,255,0), QColor(0,0,255)]
        self.text_color = QColor(255,255,255);
        self.font = QFont("Arial", 50, QFont.Bold, False)

        self.timer = QTimer()
        self.timer.setTimerType(Qt.PreciseTimer)

        self.update_timer = QTimer()
        self.update_timer.setTimerType(Qt.PreciseTimer)
        self.update_timer.setInterval(16)
        self.update_timer.timeout.connect(self.update)

        self.lsl_pull_timer = QTimer()
        self.lsl_pull_timer.setTimerType(Qt.PreciseTimer)
        self.lsl_pull_timer.setInterval(200)
        self.lsl_pull_timer.timeout.connect(self.pull_lsl)

        self.baseline_cue_duration = 3
        self.baseline_duration = 120
        self.cue_duration = 2
        self.task_duration = 4
        self.break_duration = 2
        self.cue_text = 'cue text'

        self.scene = ''
        self.stage = ''
        self.num_start_simple = 0
        self.num_subtract_simple = 0
        self.num_start_complex = 0
        self.num_subtract_complex = 0
        self.word = ''
        self.word_categories = ['Animals', 'Places', 'Shapes', 'Sport', 'Food']
        self.current_task = -1

        self.rocket_positions = np.array([[-0.5,0], [0,0], [0.5, 0]])

    def initializeGL(self):
        glClearColor(0,0,0,0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Find all images
        self.image_dir = 'images'
        self.image_files = []
        for f in os.listdir(self.image_dir):
            fname = os.path.join(self.image_dir, f)
            if os.path.isfile(fname) and fname.endswith('.png'):
                self.image_files.append(f)

        # Load all images
        self.images = {}
        for f in self.image_files:
            im = QOpenGLTexture(QImage(os.path.join(self.image_dir, f)).mirrored())
            im.setMinificationFilter(QOpenGLTexture.Linear)
            im.setMagnificationFilter(QOpenGLTexture.Linear)
            im.setWrapMode(QOpenGLTexture.ClampToBorder)
            im.setBorderColor(QColor(0,0,0,0))
            self.images[f.replace('.png', '')] = im

    def resizeGL(self, width, height):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glViewport(0,0,width,height)

    def paintGL(self):
        if self.scene == 'baseline':
            self.baselineScene()
        elif self.scene == 'training':
            self.trainingScene()
        elif self.scene == 'game':
            self.gameScene()

    def baselineScene(self):
        if self.stage == 'cue':
            self.drawTextCentered([0,0], [2, 0.5], self.cue_text, self.text_color)
        elif self.stage == 'fixation':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['fixation'])

    def trainingScene(self):
        if self.stage == 'cue_rest':
            self.drawTextCentered([0,0], [2, 0.5], 'Rest', self.text_color)
        elif self.stage == 'rest':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['fixation'])
        elif self.stage == 'cue_Auditory Imagery':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['music'])
        elif self.stage == 'cue_Facial Imagery - Celebrity':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['face_celebrity'])
            self.drawTextCentered([0,0.35], [2, 0.5], 'Celebrity', self.text_color)
        elif self.stage == 'cue_Facial Imagery - Family Member':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['face_family'])
            self.drawTextCentered([0,0.35], [2, 0.5], 'Family member', self.text_color)
        elif self.stage == 'cue_Motor Imagery - Foot':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['foot'])
        elif self.stage == 'cue_Motor Imagery - Left Hand':
            self.drawImageCentered([0,0], [0.8, 0.8], self.images['left_hand'])
        elif self.stage == 'cue_Motor Imagery - Right Hand':
            self.drawImageCentered([0,0], [0.8, 0.8], self.images['right_hand'])
        elif self.stage == 'cue_Motor Imagery - Tongue':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['tongue'])
        elif self.stage == 'cue_Shape Rotation - Cube':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['cube'])
        elif self.stage == 'cue_Shape Rotation - Complex Shape':
            self.drawImageCentered([0,-0.1], [0.8, 0.8], self.images['complex_shape'])
        elif self.stage == 'cue_Subtraction - Simple':
            self.drawTextCentered([0,0], [2, 0.5], 'Mental Math: %d - %d - %d - %d = ?' % (self.num_start_simple, self.num_subtract_simple, self.num_subtract_simple, self.num_subtract_simple), self.text_color)
        elif self.stage == 'cue_Subtraction - Complex':
            self.drawTextCentered([0,0], [2, 0.5], 'Mental Math: %d - %d - %d - %d = ?' % (self.num_start_complex, self.num_subtract_complex, self.num_subtract_complex, self.num_subtract_complex), self.text_color)
        elif self.stage == 'cue_Word Generation':
            self.drawTextCentered([0,0], [2, 0.5], 'Words: %s' % self.word, self.text_color)
        elif self.stage == 'break':
            return
        else:
            for i in range(3):
                # draw prompts
                if self.stage == self.tasks[i]:
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.7, 0.7], self.images['dotted_outline_green'])
                else:
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.7, 0.7], self.images['dotted_outline'])
                if self.tasks[i] == 'Auditory Imagery':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], self.images['music'])
                elif self.tasks[i] == 'Facial Imagery - Celebrity':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.65], [0.3, 0.3], self.images['face_celebrity'])
                    self.drawTextCentered([self.rocket_positions[i][0],-0.4], [0.3, 0.3], 'Celebrity', self.text_color, scale=0.15)
                elif self.tasks[i] == 'Facial Imagery - Family Member':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.65], [0.3, 0.3], self.images['face_family'])
                    self.drawTextCentered([self.rocket_positions[i][0],-0.4], [0.3, 0.3], 'Family member', self.text_color, scale=0.15)
                elif self.tasks[i] == 'Motor Imagery - Foot':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], self.images['foot'])
                elif self.tasks[i] == 'Motor Imagery - Left Hand':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.4, 0.4], self.images['left_hand'])
                elif self.tasks[i] == 'Motor Imagery - Right Hand':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.4, 0.4], self.images['right_hand'])
                elif self.tasks[i] == 'Motor Imagery - Tongue':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], self.images['tongue'])
                elif self.tasks[i] == 'Shape Rotation - Cube':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.33, 0.33], self.images['cube'])
                elif self.tasks[i] == 'Shape Rotation - Complex Shape':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.4, 0.4], self.images['complex_shape'])
                elif self.tasks[i] == 'Subtraction - Simple':
                    self.drawTextCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], '%d - %d - %d - %d = ?' % (self.num_start_simple, self.num_subtract_simple, self.num_subtract_simple, self.num_subtract_simple), self.text_color, scale=0.15)
                elif self.tasks[i] == 'Subtraction - Complex':
                    self.drawTextCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], '%d - %d - %d - %d = ?' % (self.num_start_complex, self.num_subtract_complex, self.num_subtract_complex, self.num_subtract_complex), self.text_color, scale=0.15)
                elif self.tasks[i] == 'Word Generation':
                    self.drawTextCentered([self.rocket_positions[i][0],-0.6], [3, 0.3], 'Words: %s' % self.word, self.text_color, scale=0.15)

                # draw rocket
                if self.rocket_positions[i][1] == 0:
                    self.drawImageCentered(self.rocket_positions[i], [0.5, 0.5], self.images['rocket'])
                else:
                    self.drawImageCentered(self.rocket_positions[i], [0.5, 0.5], self.images['rocket_blast'])
                
                # update rocket position
                if self.stage == self.tasks[i]:
                    self.rocket_positions[i][1] += 0.01
    def gameScene(self):
        if self.stage == 'cue_rest':
            self.drawTextCentered([0,0], [2, 0.5], 'Rest', self.text_color)
        elif self.stage == 'rest':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['fixation'])
        elif self.stage == 'cue_Auditory Imagery':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['music'])
        elif self.stage == 'cue_Facial Imagery - Celebrity':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['face_celebrity'])
            self.drawTextCentered([0,0.35], [2, 0.5], 'Celebrity', self.text_color)
        elif self.stage == 'cue_Facial Imagery - Family Member':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['face_family'])
            self.drawTextCentered([0,0.35], [2, 0.5], 'Family member', self.text_color)
        elif self.stage == 'cue_Motor Imagery - Foot':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['foot'])
        elif self.stage == 'cue_Motor Imagery - Left Hand':
            self.drawImageCentered([0,0], [0.8, 0.8], self.images['left_hand'])
        elif self.stage == 'cue_Motor Imagery - Right Hand':
            self.drawImageCentered([0,0], [0.8, 0.8], self.images['right_hand'])
        elif self.stage == 'cue_Motor Imagery - Tongue':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['tongue'])
        elif self.stage == 'cue_Shape Rotation - Cube':
            self.drawImageCentered([0,0], [0.5, 0.5], self.images['cube'])
        elif self.stage == 'cue_Shape Rotation - Complex Shape':
            self.drawImageCentered([0,-0.1], [0.8, 0.8], self.images['complex_shape'])
        elif self.stage == 'cue_Subtraction - Simple':
            self.drawTextCentered([0,0], [2, 0.5], 'Mental Math: %d - %d - %d - %d = ?' % (self.num_start_simple, self.num_subtract_simple, self.num_subtract_simple, self.num_subtract_simple), self.text_color)
        elif self.stage == 'cue_Subtraction - Complex':
            self.drawTextCentered([0,0], [2, 0.5], 'Mental Math: %d - %d - %d - %d = ?' % (self.num_start_complex, self.num_subtract_complex, self.num_subtract_complex, self.num_subtract_complex), self.text_color)
        elif self.stage == 'cue_Word Generation':
            self.drawTextCentered([0,0], [2, 0.5], 'Words: %s' % self.word, self.text_color)
        elif self.stage == 'break':
            for i in range(3):
                # draw prompts
                if self.stage == self.tasks[i]:
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.7, 0.7], self.images['dotted_outline_green'])
                else:
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.7, 0.7], self.images['dotted_outline'])
                if self.tasks[i] == 'Auditory Imagery':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], self.images['music'])
                elif self.tasks[i] == 'Facial Imagery - Celebrity':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.65], [0.3, 0.3], self.images['face_celebrity'])
                    self.drawTextCentered([self.rocket_positions[i][0],-0.4], [0.3, 0.3], 'Celebrity', self.text_color, scale=0.15)
                elif self.tasks[i] == 'Facial Imagery - Family Member':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.65], [0.3, 0.3], self.images['face_family'])
                    self.drawTextCentered([self.rocket_positions[i][0],-0.4], [0.3, 0.3], 'Family member', self.text_color, scale=0.15)
                elif self.tasks[i] == 'Motor Imagery - Foot':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], self.images['foot'])
                elif self.tasks[i] == 'Motor Imagery - Left Hand':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.4, 0.4], self.images['left_hand'])
                elif self.tasks[i] == 'Motor Imagery - Right Hand':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.4, 0.4], self.images['right_hand'])
                elif self.tasks[i] == 'Motor Imagery - Tongue':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], self.images['tongue'])
                elif self.tasks[i] == 'Shape Rotation - Cube':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.33, 0.33], self.images['cube'])
                elif self.tasks[i] == 'Shape Rotation - Complex Shape':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.4, 0.4], self.images['complex_shape'])
                elif self.tasks[i] == 'Subtraction - Simple':
                    self.drawTextCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], '%d - %d - %d - %d = ?' % (self.num_start_simple, self.num_subtract_simple, self.num_subtract_simple, self.num_subtract_simple), self.text_color, scale=0.15)
                elif self.tasks[i] == 'Subtraction - Complex':
                    self.drawTextCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], '%d - %d - %d - %d = ?' % (self.num_start_complex, self.num_subtract_complex, self.num_subtract_complex, self.num_subtract_complex), self.text_color, scale=0.15)
                elif self.tasks[i] == 'Word Generation':
                    self.drawTextCentered([self.rocket_positions[i][0],-0.6], [3, 0.3], 'Words: %s' % self.word, self.text_color, scale=0.15)

                # draw rocket
                if self.rocket_positions[i][1] == 0:
                    self.drawImageCentered(self.rocket_positions[i], [0.5, 0.5], self.images['rocket'])
                else:
                    self.drawImageCentered(self.rocket_positions[i], [0.5, 0.5], self.images['rocket_blast'])

                # update rocket position
                if i == self.current_task:
                    self.rocket_positions[i][1] += 0.02
        else:
            for i in range(3):
                # draw prompts
                if self.stage == self.tasks[i]:
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.7, 0.7], self.images['dotted_outline_green'])
                else:
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.7, 0.7], self.images['dotted_outline'])
                if self.tasks[i] == 'Auditory Imagery':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], self.images['music'])
                elif self.tasks[i] == 'Facial Imagery - Celebrity':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.65], [0.3, 0.3], self.images['face_celebrity'])
                    self.drawTextCentered([self.rocket_positions[i][0],-0.4], [0.3, 0.3], 'Celebrity', self.text_color, scale=0.15)
                elif self.tasks[i] == 'Facial Imagery - Family Member':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.65], [0.3, 0.3], self.images['face_family'])
                    self.drawTextCentered([self.rocket_positions[i][0],-0.4], [0.3, 0.3], 'Family member', self.text_color, scale=0.15)
                elif self.tasks[i] == 'Motor Imagery - Foot':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], self.images['foot'])
                elif self.tasks[i] == 'Motor Imagery - Left Hand':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.4, 0.4], self.images['left_hand'])
                elif self.tasks[i] == 'Motor Imagery - Right Hand':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.4, 0.4], self.images['right_hand'])
                elif self.tasks[i] == 'Motor Imagery - Tongue':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], self.images['tongue'])
                elif self.tasks[i] == 'Shape Rotation - Cube':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.33, 0.33], self.images['cube'])
                elif self.tasks[i] == 'Shape Rotation - Complex Shape':
                    self.drawImageCentered([self.rocket_positions[i][0],-0.6], [0.4, 0.4], self.images['complex_shape'])
                elif self.tasks[i] == 'Subtraction - Simple':
                    self.drawTextCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], '%d - %d - %d - %d = ?' % (self.num_start_simple, self.num_subtract_simple, self.num_subtract_simple, self.num_subtract_simple), self.text_color, scale=0.15)
                elif self.tasks[i] == 'Subtraction - Complex':
                    self.drawTextCentered([self.rocket_positions[i][0],-0.6], [0.3, 0.3], '%d - %d - %d - %d = ?' % (self.num_start_complex, self.num_subtract_complex, self.num_subtract_complex, self.num_subtract_complex), self.text_color, scale=0.15)
                elif self.tasks[i] == 'Word Generation':
                    self.drawTextCentered([self.rocket_positions[i][0],-0.6], [3, 0.3], 'Words: %s' % self.word, self.text_color, scale=0.15)

                # draw rocket
                if self.rocket_positions[i][1] == 0:
                    self.drawImageCentered(self.rocket_positions[i], [0.5, 0.5], self.images['rocket'])
                else:
                    self.drawImageCentered(self.rocket_positions[i], [0.5, 0.5], self.images['rocket_blast'])

    def drawImageCentered(self, center, size, image):
        # center = [center_x, center_y], size = [size_x, size_y]
        positions = [center[0] - size[0]/2, center[1] - size[1]/2, center[0] + size[0]/2, center[1] + size[1]/2]
        self.drawImage(positions, image)

    def drawImage(self, positions, image):
        # scale positions to maintain image aspect ratio and fit within button
        width = abs(positions[2] - positions[0])
        height = abs(positions[3] - positions[1])
        if width * self.width() <= height * self.height():
            left = positions[0]
            right = positions[2]
            top = (positions[3] + positions[1]) / 2 - (width / image.width() * image.height() / self.height() * self.width()) / 2
            bottom = (positions[3] + positions[1]) / 2 + (width / image.width() * image.height() / self.height() * self.width()) / 2
        else:
            left = (positions[2] + positions[0]) / 2 - (height / image.height() * image.width() / self.width() * self.height()) / 2
            right = (positions[2] + positions[0]) / 2 + (height / image.height() * image.width() / self.width() * self.height()) / 2
            top = positions[1]
            bottom = positions[3]

        # Render image
        # glColor3f(1., 1., 1.)
        glDisable(GL_DEPTH_TEST)
        glDepthMask(GL_FALSE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glBindTexture(GL_TEXTURE_2D, image.textureId())
        glEnable(GL_TEXTURE_2D)

        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex2f(left,top)
        glTexCoord2f(0,1); glVertex2f(left,bottom)
        glTexCoord2f(1,1); glVertex2f(right,bottom)
        glTexCoord2f(1,0); glVertex2f(right,top)
        glEnd()

        glDisable(GL_TEXTURE_2D)

        glEnable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)
        glDepthMask(GL_TRUE)

    def drawTextCentered(self, center, size, text, color, font=None, scale=None):
        positions = [center[0] - size[0]/2, center[1] + size[1]/2, center[0] + size[0]/2, center[1] - size[1]/2]
        self.drawText(positions, text, color, font, scale)

    def drawText(self, positions, text, color, font=None, scale=None):
        if not font:
            font = self.font
        if not scale:
            scale = 0.3
        # convert positions to rect
        pos = []
        pos.append(int((positions[0] + 1.) / 2. * self.width()))
        pos.append(int((1-(positions[1] + 1.) / 2.) * self.height()))
        pos.append(int(((positions[2]-positions[0])) / 2. * self.width()))
        pos.append(int((1-((positions[3]-positions[1]) / 2.) * self.height())))
        rect = QRect(pos[0], pos[1], pos[2], pos[3])

        # draw text at rect
        self.painter = QPainter(self)
        self.painter.setRenderHint(QPainter.TextAntialiasing)
        self.painter.setPen(color)
        font.setPointSizeF(abs(pos[3]) * scale)
        self.painter.setFont(font)
        self.painter.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter, text)
        self.painter.end()

    def startBaseline(self, parent):
        self.ui = parent.ui

        self.stream_info = StreamInfo(self.ui.lsl_marker_outlet_lineEdit.text(), 'Markers', 1, 0, 'string', 'bci_hoops')
        self.stream_outlet = StreamOutlet(self.stream_info)
        print("LSL Marker Outlet Stream Initialized")
        for i in range(3):
            self.stream_outlet.push_sample(['initialize baseline'])

        self.scene = 'baseline'
        self.stage = 'cue'
        self.stream_outlet.push_sample(['cue'])
        self.cue_remaining_time = self.baseline_cue_duration
        self.cue_text = 'Starting in %d...' % self.cue_remaining_time
        self.timer.timeout.connect(self.baseline_timer_timeout)
        self.timer.start(1000)

    def baseline_timer_timeout(self):
        self.cue_remaining_time -= 1
        self.cue_text = 'Starting in %d...' % self.cue_remaining_time
        if self.cue_remaining_time == 0:
            self.timer.stop()
            self.timer.timeout.disconnect(self.baseline_timer_timeout)
            self.stream_outlet.push_sample(['baseline'])
            self.stage = 'fixation'
            self.timer.timeout.connect(self.stop)
            self.timer.start(self.baseline_duration * 1000)
        self.update()

    def startTraining(self, parent):
        self.ui = parent.ui

        # get tasks
        self.tasks = [self.ui.task1_comboBox.currentText(), self.ui.task2_comboBox.currentText(), self.ui.task3_comboBox.currentText()]

        # generate randomized trials
        num_trials = int(self.ui.num_trials_lineEdit.text())
        self.trials = [0,1,2] * math.ceil(num_trials / 3)
        self.trials = self.trials[:num_trials]
        random.shuffle(self.trials)
        print('trials: ', self.trials)
        self.current_trial = 0
        self.ui.trial_label.setText('Trial: %d / %d' % (self.current_trial + 1, len(self.trials)))
        self.ui.score_label.setText('')

        if 'Subtraction - Simple' in self.tasks:
            self.num_start_simple = random.randint(51, 100)
            self.num_subtract_simple = random.randint(3,10)
        if 'Subtraction - Complex' in self.tasks:
            self.num_start_complex = random.randint(100, 200)
            self.num_subtract_complex = random.randint(3,10)
        if 'Word Generation' in self.tasks:
            self.word = random.choice(self.word_categories)

        self.stream_info = StreamInfo(self.ui.lsl_marker_outlet_lineEdit.text(), 'Markers', 1, 0, 'string', 'bci_hoops')
        self.stream_outlet = StreamOutlet(self.stream_info)
        print("LSL Marker Outlet Stream Initialized")
        for i in range(3):
            self.stream_outlet.push_sample(['initialize training'])

        self.scene = 'training'
        self.stage = 'cue_rest'
        self.stream_outlet.push_sample([self.stage])
        self.timer.timeout.connect(self.training_timer_timeout)
        self.timer.start(self.cue_duration * 1000)

    def training_timer_timeout(self):
        self.timer.stop()
        self.update_timer.stop()
        if self.stage == 'cue_rest':
            self.stage = 'rest'
            self.stream_outlet.push_sample([self.stage])
            self.timer.start(self.task_duration * 1000)
        elif self.stage == 'rest':
            if self.tasks[self.trials[self.current_trial]] == 'Subtraction - Simple':
                self.num_start_simple = random.randint(51, 100)
                self.num_subtract_simple = random.randint(3,10)
            elif self.tasks[self.trials[self.current_trial]] == 'Subtraction - Complex':
                self.num_start_complex = random.randint(100, 200)
                self.num_subtract_complex = random.randint(3,10)
            elif self.tasks[self.trials[self.current_trial]] == 'Word Generation':
                self.word = random.choice(self.word_categories)
            self.stage = 'cue_%s' % self.tasks[self.trials[self.current_trial]]
            self.stream_outlet.push_sample([self.stage])
            self.timer.start(self.cue_duration * 1000)
        elif self.stage == 'cue_%s' % self.tasks[self.trials[self.current_trial]]:
            self.stage = self.tasks[self.trials[self.current_trial]]
            self.stream_outlet.push_sample([self.stage])
            self.timer.start(self.task_duration * 1000)
            self.update_timer.start()
            self.rocket_positions = np.array([[-0.5,0], [0,0], [0.5, 0]])
        elif self.stage == self.tasks[self.trials[self.current_trial]]:
            self.stage = 'break'
            self.stream_outlet.push_sample([self.stage])
            self.timer.start(self.break_duration * 1000)
        elif self.stage == 'break':
            self.current_trial += 1
            self.ui.trial_label.setText('Trial: %d / %d' % (self.current_trial + 1, len(self.trials)))
            if self.current_trial < len(self.trials):
                self.stage = 'cue_rest'
                self.stream_outlet.push_sample([self.stage])
                self.timer.start(self.cue_duration * 1000)
            else:
                self.stop()
        self.update()

    def startGame(self, parent):
        self.ui = parent.ui

        # get tasks
        self.tasks = [self.ui.task1_comboBox.currentText(), self.ui.task2_comboBox.currentText(), self.ui.task3_comboBox.currentText()]

        # generate randomized trials
        num_trials = int(self.ui.num_trials_lineEdit.text())
        self.trials = [0,1,2] * math.ceil(num_trials / 3)
        self.trials = self.trials[:num_trials]
        random.shuffle(self.trials)
        print('trials: ', self.trials)
        self.current_trial = 0
        self.current_score = 0
        self.ui.trial_label.setText('Trial: %d / %d' % (self.current_trial + 1, len(self.trials)))
        self.ui.score_label.setText('Score: %d / %d' % (self.current_score, len(self.trials)))

        if 'Subtraction - Simple' in self.tasks:
            self.num_start_simple = random.randint(51, 100)
            self.num_subtract_simple = random.randint(3,10)
        if 'Subtraction - Complex' in self.tasks:
            self.num_start_complex = random.randint(100, 200)
            self.num_subtract_complex = random.randint(3,10)
        if 'Word Generation' in self.tasks:
            self.word = random.choice(self.word_categories)

        # LSL
        self.resolver = ContinuousResolver()
        self.streams = self.resolver.results()
        self.stream_inlet = None
        for info in self.streams:
            if info.name() == self.ui.lsl_prediction_inlet_lineEdit.text():
                self.stream_inlet = StreamInlet(info)
                break
        if not self.stream_inlet:
            self.ui.lsl_stream_label.setText('LSL stream not found')
            print('Cannot find LSL inlet stream: %s' % self.ui.lsl_prediction_inlet_lineEdit.text())
        else:
            self.ui.lsl_stream_label.setText('')
            
        self.stream_info = StreamInfo(self.ui.lsl_marker_outlet_lineEdit.text(), 'Markers', 1, 0, 'string', 'bci_hoops')
        self.stream_outlet = StreamOutlet(self.stream_info)
        print("LSL Marker Outlet Stream Initialized")
        for i in range(3):
            self.stream_outlet.push_sample(['initialize game'])

        self.current_task = -1
        self.scene = 'game'
        self.stage = 'cue_rest'
        self.stream_outlet.push_sample([self.stage])
        self.timer.timeout.connect(self.game_timer_timeout)
        self.timer.start(self.cue_duration * 1000)

    def game_timer_timeout(self):
        self.timer.stop()
        self.update_timer.stop()
        if self.stage == 'cue_rest':
            self.stage = 'rest'
            self.stream_outlet.push_sample([self.stage])
            self.timer.start(self.task_duration * 1000)
        elif self.stage == 'rest':
            if self.tasks[self.trials[self.current_trial]] == 'Subtraction - Simple':
                self.num_start_simple = random.randint(51, 100)
                self.num_subtract_simple = random.randint(3,10)
            elif self.tasks[self.trials[self.current_trial]] == 'Subtraction - Complex':
                self.num_start_complex = random.randint(100, 200)
                self.num_subtract_complex = random.randint(3,10)
            elif self.tasks[self.trials[self.current_trial]] == 'Word Generation':
                self.word = random.choice(self.word_categories)
            self.current_task = -1
            self.stage = 'cue_%s' % self.tasks[self.trials[self.current_trial]]
            self.stream_outlet.push_sample([self.stage])
            self.timer.start(self.cue_duration * 1000)
        elif self.stage == 'cue_%s' % self.tasks[self.trials[self.current_trial]]:
            self.stage = self.tasks[self.trials[self.current_trial]]
            self.stream_outlet.push_sample([self.stage])
            self.timer.start(self.task_duration * 1000)
            self.update_timer.start()
            self.rocket_positions = np.array([[-0.5,0], [0,0], [0.5, 0]])
        elif self.stage == self.tasks[self.trials[self.current_trial]]:
            self.stage = 'break'
            self.stream_outlet.push_sample([self.stage])
            self.timer.start(self.break_duration * 1000)
            self.update_timer.start()
            self.lsl_pull_timer.stop()

            print('current task = %d' % self.current_task)
            if self.current_task == self.trials[self.current_trial]:
                self.current_score += 1
                self.ui.score_label.setText('Score: %d / %d' % (self.current_score, len(self.trials)))
        elif self.stage == 'break':
            self.current_trial += 1
            self.ui.trial_label.setText('Trial: %d / %d' % (self.current_trial + 1, len(self.trials)))
            if self.current_trial < len(self.trials):
                self.stage = 'cue_rest'
                self.stream_outlet.push_sample([self.stage])
                self.timer.start(self.cue_duration * 1000)
            else:
                self.stop()
        self.update()

    def selectTask(self, taskNum):
        if not taskNum in [0,1,2]:
            return
        self.current_task = taskNum
        print('task = %d' % self.current_task)

    def pull_lsl(self):
        if self.stream_inlet:
            sample, _ = self.stream_inlet.pull_sample()
            if sample[0].startswith('task='):
                self.selectTask(sample[0].replace('task=', ''))

    def stop(self):
        self.timer.stop()
        self.lsl_pull_timer.stop()
        try:
            self.timer.timeout.disconnect()
        except:
            pass
        self.update_timer.stop()
        self.ui.stackedWidget.setCurrentWidget(self.ui.home_page)