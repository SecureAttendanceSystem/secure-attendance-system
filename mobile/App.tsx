
import { useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";

type Screen = "login" | "signup" | "enroll" | "dashboard";

export default function App() {
  const [screen, setScreen] = useState<Screen>("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const validEmail = (value: string) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

  function handleLogin() {
    if (!validEmail(email) || !password.trim()) {
      Alert.alert("Invalid details", "Enter an email and password.");
      return;
    }

    // Demo only: no real authentication yet.
    setScreen("dashboard");
  }

  function handleSignup() {
    if (!fullName.trim()) {
      Alert.alert("Missing name", "Please enter your full name.");
      return;
    }

    if (!validEmail(email)) {
      Alert.alert("Invalid email", "Enter a valid university email.");
      return;
    }

    if (password.length < 8) {
      Alert.alert("Weak password", "Use at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      Alert.alert("Password mismatch", "Passwords do not match.");
      return;
    }

    // UI prototype: no account is actually created.
    setPassword("");
    setConfirmPassword("");
    setScreen("enroll");
  }

  const isSignup = screen === "signup";
  const isAuthScreen = screen === "login" || isSignup;

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <StatusBar style="dark" />

      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.brand}>
          <View style={styles.logo}>
            <Text style={styles.logoText}>SA</Text>
          </View>
          <Text style={styles.university}>
            UNIVERSITY OF NEW BRUNSWICK
          </Text>
        </View>

        <View style={styles.card}>
          {isAuthScreen && (
            <>
              <Text style={styles.eyebrow}>SECURE ATTENDANCE</Text>
              <Text style={styles.title}>
                {isSignup ? "Create your account" : "Welcome back"}
              </Text>
              <Text style={styles.subtitle}>
                {isSignup
                  ? "Register to access your attendance system."
                  : "Sign in to your university account."}
              </Text>

              <View style={styles.tabs}>
                <Pressable
                  style={[
                    styles.tab,
                    !isSignup && styles.activeTab,
                  ]}
                  onPress={() => setScreen("login")}
                >
                  <Text style={[
                    styles.tabText,
                    !isSignup && styles.activeTabText,
                  ]}>
                    Log in
                  </Text>
                </Pressable>

                <Pressable
                  style={[
                    styles.tab,
                    isSignup && styles.activeTab,
                  ]}
                  onPress={() => setScreen("signup")}
                >
                  <Text style={[
                    styles.tabText,
                    isSignup && styles.activeTabText,
                  ]}>
                    Sign up
                  </Text>
                </Pressable>
              </View>

              {isSignup && (
                <>
                  <Text style={styles.label}>Full name</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="Enter your full name"
                    placeholderTextColor="#94A3B8"
                    value={fullName}
                    onChangeText={setFullName}
                    autoComplete="name"
                  />
                </>
              )}

              <Text style={styles.label}>University email</Text>
              <TextInput
                style={styles.input}
                placeholder="you@unb.ca"
                placeholderTextColor="#94A3B8"
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
                autoComplete="email"
              />

              <Text style={styles.label}>Password</Text>
              <View style={styles.passwordRow}>
                <TextInput
                  style={styles.passwordInput}
                  placeholder="Enter your password"
                  placeholderTextColor="#94A3B8"
                  secureTextEntry={!showPassword}
                  value={password}
                  onChangeText={setPassword}
                  autoComplete={
                    isSignup ? "new-password" : "current-password"
                  }
                />
                <Pressable
                  onPress={() => setShowPassword(!showPassword)}
                >
                  <Text style={styles.showText}>
                    {showPassword ? "Hide" : "Show"}
                  </Text>
                </Pressable>
              </View>

              {isSignup && (
                <>
                  <Text style={styles.label}>Confirm password</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="Confirm your password"
                    placeholderTextColor="#94A3B8"
                    secureTextEntry={!showPassword}
                    value={confirmPassword}
                    onChangeText={setConfirmPassword}
                    autoComplete="new-password"
                  />
                </>
              )}

              <Pressable
                style={styles.button}
                onPress={isSignup ? handleSignup : handleLogin}
              >
                <Text style={styles.buttonText}>
                  {isSignup ? "Continue" : "Log in"}
                </Text>
              </Pressable>

              <Text style={styles.demo}>
                Demo mode — no account data is saved.
              </Text>
            </>
          )}

          {screen === "enroll" && (
            <>
              <Text style={styles.eyebrow}>FACE ENROLLMENT</Text>
              <Text style={styles.title}>Set up face verification</Text>
              <Text style={styles.subtitle}>
                For attendance sessions requiring Level 3 security,
                students may register a facial reference once.
              </Text>

              <View style={styles.infoBox}>
                <Text style={styles.infoTitle}>Camera setup</Text>
                <Text style={styles.infoDescription}>
                  Next, we'll add camera access, selfie capture,
                  and a review screen. Your photo will not be
                  uploaded during this step.
                </Text>
              </View>

              <Pressable
                style={styles.button}
                onPress={() => setScreen("dashboard")}
              >
                <Text style={styles.buttonText}>
                  Skip enrollment for now
                </Text>
              </Pressable>

              <Pressable
                style={styles.secondaryButton}
                onPress={() => setScreen("signup")}
              >
                <Text style={styles.secondaryText}>Back to sign up</Text>
              </Pressable>
            </>
          )}

          {screen === "dashboard" && (
            <>
              <Text style={styles.eyebrow}>STUDENT PORTAL</Text>
              <Text style={styles.title}>Welcome to SUA</Text>
              <Text style={styles.subtitle}>
                This is a temporary dashboard for testing navigation.
              </Text>

              <View style={styles.infoBox}>
                <Text style={styles.infoTitle}>Face enrollment</Text>
                <Text style={styles.infoDescription}>
                  Not enrolled. The camera capture feature will be
                  implemented next.
                </Text>
              </View>

              <Pressable
                style={styles.button}
                onPress={() => setScreen("enroll")}
              >
                <Text style={styles.buttonText}>
                  Open face enrollment
                </Text>
              </Pressable>

              <Pressable
                style={styles.secondaryButton}
                onPress={() => {
                  setPassword("");
                  setScreen("login");
                }}
              >
                <Text style={styles.secondaryText}>Back to login</Text>
              </Pressable>
            </>
          )}
        </View>

        <Text style={styles.footer}>
          Secure University Attendance System
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F7FB",
  },
  content: {
    flexGrow: 1,
    justifyContent: "center",
    padding: 24,
    paddingTop: 60,
    paddingBottom: 40,
  },
  brand: {
    alignItems: "center",
    marginBottom: 28,
  },
  logo: {
    backgroundColor: "#193B67",
    width: 56,
    height: 56,
    borderRadius: 14,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 12,
  },
  logoText: {
    color: "#FFFFFF",
    fontSize: 22,
    fontWeight: "700",
  },
  university: {
    fontSize: 11,
    letterSpacing: 1.5,
    color: "#64748B",
    fontWeight: "600",
    textAlign: "center",
  },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 26,
    width: "100%",
    maxWidth: 460,
    alignSelf: "center",
    borderWidth: 1,
    borderColor: "#E6EAF0",
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: "700",
    color: "#426F9D",
    letterSpacing: 1.5,
    marginBottom: 12,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    color: "#172B49",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: "#64748B",
    lineHeight: 22,
    marginBottom: 25,
  },
  tabs: {
    flexDirection: "row",
    backgroundColor: "#F1F5F9",
    borderRadius: 10,
    padding: 4,
    marginBottom: 25,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: "center",
    borderRadius: 8,
  },
  activeTab: {
    backgroundColor: "#FFFFFF",
    elevation: 2,
  },
  tabText: {
    color: "#64748B",
    fontWeight: "600",
  },
  activeTabText: {
    color: "#193B67",
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: "#334155",
    marginBottom: 9,
  },
  input: {
    height: 52,
    borderWidth: 1,
    borderColor: "#DCE3EC",
    borderRadius: 10,
    paddingHorizontal: 14,
    fontSize: 15,
    color: "#172B49",
    marginBottom: 20,
  },
  passwordRow: {
    height: 52,
    borderWidth: 1,
    borderColor: "#DCE3EC",
    borderRadius: 10,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    marginBottom: 20,
  },
  passwordInput: {
    flex: 1,
    fontSize: 15,
    color: "#172B49",
  },
  showText: {
    color: "#315F91",
    fontSize: 13,
    fontWeight: "600",
    padding: 6,
  },
  button: {
    backgroundColor: "#193B67",
    borderRadius: 10,
    height: 52,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "700",
  },
  secondaryButton: {
    alignItems: "center",
    padding: 15,
    marginTop: 8,
  },
  secondaryText: {
    color: "#315F91",
    fontSize: 14,
    fontWeight: "600",
  },
  infoBox: {
    backgroundColor: "#F1F5F9",
    borderRadius: 12,
    padding: 18,
    marginBottom: 20,
  },
  infoTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#172B49",
    marginBottom: 8,
  },
  infoDescription: {
    fontSize: 13,
    color: "#64748B",
    lineHeight: 21,
  },
  demo: {
    fontSize: 12,
    color: "#94A3B8",
    textAlign: "center",
    marginTop: 20,
  },
  footer: {
    textAlign: "center",
    fontSize: 12,
    color: "#94A3B8",
    marginTop: 28,
  },
});
