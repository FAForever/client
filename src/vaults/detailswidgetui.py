from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFormLayout
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtWidgets import QSizePolicy
from PyQt6.QtWidgets import QSpacerItem
from PyQt6.QtWidgets import QTableWidget
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.qt.widgets.clickablelabel import ClickableLabel


class DetailsWidgetUI:
    def setupUi(self, widget: QWidget) -> None:
        self.mainLayout = QVBoxLayout(widget)
        self.tabs = QTabWidget()

        overview_widget = QScrollArea()
        overview_widget.setWidgetResizable(True)
        overview_widget.setObjectName("overview_widget")
        overview_content = QWidget()
        overview_content.setObjectName("overview_content")
        self.overviewLayout = QVBoxLayout(overview_content)

        self.headerLayout = QHBoxLayout()

        self.titleLayout = QVBoxLayout()
        self.titleLabel = QLabel()
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.titleLabel.setFont(title_font)

        self.typeLabel = QLabel()
        type_font = QFont()
        type_font.setPointSize(10)
        type_font.setItalic(True)
        self.typeLabel.setFont(type_font)

        self.titleLayout.addWidget(self.titleLabel)
        self.titleLayout.addWidget(self.typeLabel)

        self.statsLayout = QVBoxLayout()
        self.additionalInfoLabel = QLabel()

        self.statsLayout.addWidget(self.additionalInfoLabel)
        self.statsLayout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.headerLayout.addLayout(self.titleLayout, 7)
        self.headerLayout.addLayout(self.statsLayout, 3)
        self.overviewLayout.addLayout(self.headerLayout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.overviewLayout.addWidget(line)

        content_layout = QGridLayout()

        self.thumbnailLabel = ClickableLabel("Loading thumbnail...")
        self.thumbnailLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnailLabel.setMinimumSize(200, 150)
        content_layout.addWidget(self.thumbnailLabel, 0, 0, 3, 1)

        author_box = QGroupBox("Author")
        self.authorLayout = QFormLayout()

        author_box.setLayout(self.authorLayout)
        content_layout.addWidget(author_box, 0, 1)

        reviews_box = QGroupBox("Reviews")
        self.reviewsLayout = QVBoxLayout()
        self.reviewsForm = QFormLayout()
        self.reviewsLayout.addLayout(self.reviewsForm)

        self.noReviewsLabel = QLabel("No reviews available")
        self.reviewsLayout.addWidget(self.noReviewsLabel)

        self.viewReviewsButton = QPushButton("View All Reviews")
        self.reviewsLayout.addWidget(self.viewReviewsButton)

        self.addReviewButton = QPushButton("Add Review")
        self.reviewsLayout.addWidget(self.addReviewButton)

        reviews_box.setLayout(self.reviewsLayout)
        content_layout.addWidget(reviews_box, 1, 1)

        version_box = QGroupBox("Version Details")
        self.versionLayout = QFormLayout()

        version_box.setLayout(self.versionLayout)
        content_layout.addWidget(version_box, 2, 1)

        self.overviewLayout.addLayout(content_layout)

        description_box = QGroupBox("Description")
        descriptionLayout = QVBoxLayout()
        self.descriptionLabel = QLabel()
        self.descriptionLabel.setWordWrap(True)
        descriptionLayout.addWidget(self.descriptionLabel)
        description_box.setLayout(descriptionLayout)
        self.overviewLayout.addWidget(description_box)

        buttonLayout = QHBoxLayout()

        spacer = QSpacerItem(5, 5, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        buttonLayout.addItem(spacer)
        self.downloadButton = QPushButton()
        self.downloadButton.setProperty("download", "true")
        buttonLayout.addWidget(self.downloadButton)
        self.removeButton = QPushButton()
        self.removeButton.setProperty("remove", "true")
        buttonLayout.addWidget(self.removeButton)

        self.viewFolderButton = QPushButton("View Files")
        buttonLayout.addWidget(self.viewFolderButton)

        self.overviewLayout.addStretch()
        overview_widget.setWidget(overview_content)
        self.tabs.addTab(overview_widget, "Overview")

        tech_widget = QWidget()
        tech_widget.setObjectName("tech_widget")
        tech_layout = QVBoxLayout()

        self.techTable = QTableWidget()
        self.techTable.setColumnCount(2)
        self.techTable.setHorizontalHeaderLabels(["Property", "Value"])
        self.techTable.resizeColumnsToContents()
        tech_layout.addWidget(self.techTable)

        tech_widget.setLayout(tech_layout)
        self.tabs.addTab(tech_widget, "Technical Details")

        self.detailedReviews = ReviewsWidgetUI()
        self.tabs.addTab(self.detailedReviews, "Reviews")
        self.mainLayout.addWidget(self.tabs)
        self.mainLayout.addLayout(buttonLayout)


class ReviewsWidgetUI(QScrollArea):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.init_ui()

    def show_reviews(self) -> None:
        self.loadingLabel.hide()
        self.noReviewsLabel.hide()
        self.contentWidget.show()

    def show_no_reviews(self) -> None:
        self.loadingLabel.hide()
        self.noReviewsLabel.show()
        self.contentWidget.hide()

    def show_loading(self) -> None:
        self.loadingLabel.show()
        self.noReviewsLabel.hide()
        self.contentWidget.hide()

    def create_content_widget(self) -> QWidget:
        contentWidget = QWidget()
        content_layout = QVBoxLayout()

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(separator)

        self.ratingBarsLayout = QVBoxLayout()
        content_layout.addLayout(self.ratingBarsLayout)

        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(separator2)

        content_layout.addWidget(QLabel("Comments"))
        self.addCommentButton = QPushButton("Add Comment")
        content_layout.addWidget(self.addCommentButton)
        self.commentsContainer = QVBoxLayout()
        content_layout.addLayout(self.commentsContainer)
        contentWidget.setLayout(content_layout)
        return contentWidget

    def init_ui(self) -> None:
        self.setWidgetResizable(True)
        self.setObjectName("overview_widget")
        reviews_content = QWidget()
        reviews_content.setObjectName("overview_content")
        self.main_layout = QVBoxLayout(reviews_content)

        self.loadingLabel = QLabel("Loading reviews...")
        self.loadingLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.loadingLabel.font()
        font.setPointSize(20)
        font.setBold(True)
        self.loadingLabel.setFont(font)
        self.main_layout.addWidget(self.loadingLabel)

        self.noReviewsLabel = QLabel("No reviews available for this map.")
        self.noReviewsLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.noReviewsLabel.font()
        font.setPointSize(20)
        font.setBold(True)
        self.noReviewsLabel.setFont(font)
        self.main_layout.addWidget(self.noReviewsLabel)

        self.contentWidget = self.create_content_widget()
        self.main_layout.addWidget(self.contentWidget)

        self.setWidget(reviews_content)

        self.noReviewsLabel.hide()
        self.loadingLabel.hide()
        self.contentWidget.hide()
